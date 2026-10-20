#!/usr/bin/env python3
"""Run PR04 against real ROS processes; assert every reported result."""

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from geometry_msgs.msg import Twist
import rclpy

from ros_support import cli, Observer, stop


def measure(observer, expected_hz, seconds=4.0):
    """Measure received messages after draining old queued samples."""
    observer.spin_for(0.5)
    observer.samples.clear()
    observer.source_samples.clear()
    started = time.monotonic()
    observer.spin_for(seconds)
    duration = time.monotonic() - started
    samples = list(observer.samples)
    assert len(samples) >= 3, samples
    rate = (len(samples) - 1) / (samples[-1][0] - samples[0][0])
    count_rate = len(samples) / duration
    result = {'duration_s': duration, 'messages': len(samples), 'hz': rate,
              'count_hz': count_rate, 'expected_hz': expected_hz}
    stamps = observer.source_samples
    if len(stamps) >= 2 and stamps[-1] > stamps[0]:
        result['source_hz'] = (len(stamps) - 1) * 1e9 / (stamps[-1] - stamps[0])
    print('MEASURE', json.dumps(result), flush=True)
    assert 0.8 * expected_hz <= rate <= 1.2 * expected_hz, rate
    assert 0.8 * expected_hz <= count_rate <= 1.2 * expected_hz, count_rate
    return result


def command(observer, *args, timeout=15, allow_failure=False):
    """Run a real CLI query while continuing to receive ROS data."""
    argv = ['ros2', *args]
    if args[0] == 'param':
        # Jazzy wait_for_node bounds discovery; avoid stale daemon snapshots.
        argv += ['--no-daemon', '--spin-time', '2', '--timeout', '8']
    print('$', ' '.join(argv), flush=True)
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    timed_out = False
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None and time.monotonic() < deadline:
            observer.spin_for(0.05)
        if process.poll() is None:
            timed_out = True
            os.killpg(process.pid, signal.SIGINT)
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    print(f'exit={process.returncode}; timeout={timed_out}', flush=True)
    print(stdout, end='', flush=True)
    if stderr:
        print('stderr:\n' + stderr, flush=True)
    if not allow_failure:
        assert process.returncode == 0 and not timed_out, (stdout, stderr)
    return stdout + stderr


def set_parameter(observer, name, value, accepted):
    """Check the CLI response, which may use exit zero even for rejection."""
    text = command(observer, 'param', 'set', '/patrol', name, value,
                   allow_failure=not accepted)
    expected = 'Set parameter successful' if accepted else 'Setting parameter failed'
    assert expected in text, text
    return text


def check_value(observer, name, expected):
    """Read back the actual parameter service value."""
    text = command(observer, 'param', 'get', '/patrol', name)
    assert float(text.strip().rsplit(':', 1)[1]) == expected, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-defect', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    rclpy.init()
    observer = Observer()
    records = {}
    children = []
    with tempfile.TemporaryDirectory(prefix='pr04-runtime-') as temporary:
        def launch(*arguments):
            argv = ['ros2', *arguments]
            print('$', ' '.join(argv), flush=True)
            log_path = Path(temporary) / f'{len(children)}.log'
            with log_path.open('w') as stream:
                process = subprocess.Popen(
                    argv, stdout=stream, stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONUNBUFFERED': '1'})
            children.append((process, log_path))
            return process, log_path

        try:
            observer.spin_for(1)
            assert observer.count_publishers('/turtle1/pose') == 0, 'Use an empty domain'
            assert observer.count_publishers('/turtle1/cmd_vel') == 0
            assert 'patrol' not in observer.get_node_names()
            simulator, _ = launch('launch', 'turtle_bringup', 'sim.launch.py')
            observer.wait(lambda: observer.pose is not None)
            records['pose_type'] = cli('topic', 'type', '/turtle1/pose').strip()
            assert records['pose_type'] == 'turtlesim/msg/Pose', records
            observer.create_subscription(
                Twist, '/turtle1/cmd_vel', observer.receive_command, 10)
            patrol, patrol_log = launch(
                'run', 'patrol', 'patrol', '--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel')
            observer.wait(lambda: len(observer.samples) >= 5)
            check_value(observer, 'publish_hz', 10.0)
            check_value(observer, 'linear_speed', 0.5)
            check_value(observer, 'turn_rate', 0.3)
            records['initial'] = measure(observer, 10.0)
            assert all(v == 0.5 and w == 0.3 for _, v, w in observer.samples)
            before = observer.coordinates()
            observer.spin_for(0.5)
            after = observer.coordinates()
            assert math.hypot(after[0] - before[0], after[1] - before[1]) > 0.02
            records['initial_motion'] = {'before': before, 'after': after}
            if args.expect_defect:
                records['zero_response'] = command(
                    observer, 'param', 'set', '/patrol', 'publish_hz', '0.0',
                    timeout=8, allow_failure=True)
                observer.wait(lambda: patrol.poll() is not None)
                failure = patrol_log.read_text()
                assert patrol.returncode != 0
                assert 'ZeroDivisionError' in failure and 'period = 1.0 /' in failure
                observer.wait(lambda: observer.count_publishers('/turtle1/cmd_vel') == 0)
                records['patrol_exit'] = patrol.returncode
                records['traceback'] = failure
                records['defect_reproduced'] = True
                print('PASS defect reproduced: publish_hz=0.0 raised ZeroDivisionError; '
                      'patrol exited and its publisher disappeared', flush=True)
            else:
                records['zero_response'] = set_parameter(
                    observer, 'publish_hz', '0.0', accepted=False)
                check_value(observer, 'publish_hz', 10.0)
                records['after_zero_at_10'] = measure(observer, 10.0)
                for value in ['-1.0', '.nan', '.inf', '31.0']:
                    set_parameter(observer, 'publish_hz', value, accepted=False)
                    check_value(observer, 'publish_hz', 10.0)
                records['after_invalids_at_10'] = measure(observer, 10.0)
                set_parameter(observer, 'publish_hz', '5.0', accepted=True)
                check_value(observer, 'publish_hz', 5.0)
                records['at_5'] = measure(observer, 5.0)
                set_parameter(observer, 'publish_hz', '0.0', accepted=False)
                check_value(observer, 'publish_hz', 5.0)
                records['after_zero_at_5'] = measure(observer, 5.0)
                set_parameter(observer, 'linear_speed', '0.8', accepted=True)
                set_parameter(observer, 'turn_rate', '-0.6', accepted=True)
                observer.spin_for(0.5)
                observer.samples.clear()
                observer.spin_for(1.0)
                assert len(observer.samples) >= 4
                assert all(v == 0.8 and w == -0.6 for _, v, w in observer.samples)
                records['changed_twist'] = {'linear_x': 0.8, 'angular_z': -0.6,
                                            'messages': len(observer.samples)}
                set_parameter(observer, 'linear_speed', '1.1', accepted=False)
                set_parameter(observer, 'turn_rate', '-1.1', accepted=False)
                check_value(observer, 'linear_speed', 0.8)
                check_value(observer, 'turn_rate', -0.6)
                records['clear'] = command(observer, 'service', 'call', '/clear',
                                           'std_srvs/srv/Empty', '{}')
                assert 'response:' in records['clear']
                records['actions'] = command(observer, 'action', 'list', '-t')
                assert '/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]' in records['actions']
                stop(patrol)
                assert patrol.returncode == 0
                observer.wait(lambda: observer.count_publishers('/turtle1/cmd_vel') == 0)
                observer.spin_for(2)
                assert observer.pose.linear_velocity == observer.pose.angular_velocity == 0
                records['defect_fixed'] = True
                print('PASS PR04 runtime: rejected values preserve flow; 10 -> 5 Hz; '
                      'runtime speeds, /clear, action discovery and shutdown', flush=True)
            stop(simulator)
            assert simulator.returncode == 0
            observer.wait(lambda: 'turtlesim' not in observer.get_node_names())
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(records, indent=2) + '\n')
        finally:
            try:
                for process, log in reversed(children):
                    stop(process)
                    content = log.read_text()
                    if content:
                        print(f'PROCESS LOG {process.args}:\n{content}', flush=True)
            finally:
                observer.destroy_node()
                rclpy.try_shutdown()


if __name__ == '__main__':
    main()
