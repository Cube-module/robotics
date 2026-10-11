#!/usr/bin/env python3
"""Повторить опыт ПР03 в установленном workspace. Вывод — в stdout."""
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from patrol.patrol import Pose


class Observer(Node):
    def __init__(self):
        super().__init__('pr03_observer')
        self.pose = None
        self.samples = []
        self.create_subscription(Pose, '/turtle1/pose', self.receive_pose, 10)

    def receive_pose(self, message):
        self.pose = message

    def receive_command(self, message):
        self.samples.append((time.monotonic(), message.linear.x, message.angular.z))

    def wait(self, predicate, seconds=12):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        assert predicate(), 'Expected event did not arrive before timeout'

    def spin_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def coordinates(self):
        return [self.pose.x, self.pose.y, self.pose.theta]


def stop(child):
    if child.poll() is None:
        # Jazzy ros2 run expects terminal Ctrl+C to reach its whole group.
        # ros2 launch forwards SIGINT itself; send only to its parent.
        if child.args[:2] == ['ros2', 'run']:
            os.killpg(child.pid, signal.SIGINT)
        else:
            child.send_signal(signal.SIGINT)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            raise AssertionError('SIGINT did not stop process')


def cli(*args, expected_lines=(), seconds=20):
    # Each --no-daemon invocation has its own DDS graph. A populated Observer
    # graph does not imply that a new CLI participant has discovered it yet.
    command = ['ros2', *args, '--no-daemon', '--spin-time', '2']
    deadline = time.monotonic() + seconds
    last = 'no completed query'
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        # Give later fresh participants more discovery time (2, 4, then 8 s);
        # the shared deadline still limits the entire operation to seconds.
        command[-1] = str(2 ** min(attempt, 3))
        print('$', ' '.join(command), f'(attempt {attempt})', flush=True)
        try:
            result = subprocess.run(command, text=True, capture_output=True,
                                    timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as error:
            raise AssertionError(
                f'{command}: discovery deadline {seconds}s; last: {last}; '
                f'timed-out stdout={error.stdout!r}, stderr={error.stderr!r}') from error
        last = (f'exit={result.returncode}, stdout={result.stdout!r}, '
                f'stderr={result.stderr!r}')
        print(last, flush=True)
        lines = {line.strip() for line in result.stdout.splitlines()}
        if result.returncode == 0 and set(expected_lines) <= lines:
            return result.stdout
        # Retry only known discovery misses (type silently exits 1 in Lyrical)
        # or successful but incomplete graph snapshots. Syntax/runtime errors
        # must fail immediately, rather than being concealed by retries.
        output = (result.stdout + result.stderr).strip()
        missing = result.returncode == 1 and (
            (args[:2] == ('topic', 'type') and not output)
            or (args[:2] == ('topic', 'info') and output == f"Unknown topic '{args[2]}'")
            or (args[:2] == ('node', 'info') and output == f"Unable to find node '{args[2]}'")
        )
        if result.returncode != 0 and not missing:
            raise AssertionError(f'{command}: {last}')
        print(f'Waiting for discovery; expected lines: {expected_lines!r}', flush=True)
    raise AssertionError(f'{command}: discovery deadline {seconds}s; last: {last}')


def main():
    rclpy.init()
    observer = Observer()
    children = []
    with tempfile.TemporaryDirectory(prefix='pr03-') as directory:
        def launch(*args):
            command = ['ros2', *args]
            print('$', ' '.join(command), flush=True)
            path = Path(directory) / f'{len(children)}.log'
            with path.open('w') as log:
                child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True,
                                         env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            children.append((child, path))
            return child

        def finish_patrol(child):
            stop(child)
            assert child.returncode == 0, f'patrol exit: {child.returncode}'
            observer.wait(lambda: 'patrol' not in observer.get_node_names())

        try:
            observer.spin_for(1)
            assert observer.count_publishers('/turtle1/pose') == 0, 'Use an empty ROS domain'
            assert observer.count_publishers('/turtle1/cmd_vel') == 0
            command_sub = observer.create_subscription(Twist, '/turtle1/cmd_vel', observer.receive_command, 10)
            patrol = launch('run', 'patrol', 'patrol', '--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel')
            observer.wait(lambda: len(observer.samples) >= 5)
            assert all(v == w == 0 for _, v, w in observer.samples)
            print('PASS no Pose: five zero Twist messages', flush=True)
            finish_patrol(patrol)
            observer.destroy_subscription(command_sub)

            simulator = launch('launch', 'turtle_bringup', 'sim.launch.py')
            observer.wait(lambda: observer.pose is not None)
            pose_type = f"{Pose.__module__.split('.')[0]}/msg/Pose"
            cli('topic', 'type', '/turtle1/pose', expected_lines=(pose_type,))
            before = observer.coordinates()
            patrol = launch('run', 'patrol', 'patrol')
            observer.wait(lambda: observer.count_publishers('/cmd_vel') == 1)
            observer.wait(lambda: observer.count_subscribers('/turtle1/pose') >= 2)
            cli('node', 'info', '/patrol', expected_lines=(
                f'/turtle1/pose: {pose_type}', '/cmd_vel: geometry_msgs/msg/Twist'))
            cli('topic', 'info', '/cmd_vel', '--verbose', expected_lines=(
                'Publisher count: 1', 'Subscription count: 0'))
            observer.wait(lambda: observer.count_subscribers('/turtle1/cmd_vel') == 1)
            cli('topic', 'info', '/turtle1/cmd_vel', '--verbose', expected_lines=(
                'Publisher count: 0', 'Subscription count: 1'))
            observer.spin_for(2)
            broken = observer.coordinates()
            assert all(abs(a-b) < 1e-5 for a, b in zip(before, broken))
            print(f'PASS defect: before={before}; after={broken}; pose unchanged', flush=True)
            finish_patrol(patrol)

            patrol = launch('run', 'patrol', 'patrol', '--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel')
            observer.wait(lambda: observer.count_publishers('/turtle1/cmd_vel') == 1)
            cli('topic', 'info', '/turtle1/cmd_vel', '--verbose', expected_lines=(
                'Publisher count: 1', 'Subscription count: 1'))
            command_sub = observer.create_subscription(Twist, '/turtle1/cmd_vel', observer.receive_command, 10)
            observer.spin_for(1)
            observer.samples.clear()
            hz = launch('topic', 'hz', '/turtle1/cmd_vel')
            start = time.monotonic()
            observer.spin_for(10)
            duration = time.monotonic() - start
            stop(hz)
            print('ros2 topic hz (10 second observation):\n' + children[-1][1].read_text(), flush=True)
            assert len(observer.samples) >= 80, len(observer.samples)
            rate = (len(observer.samples)-1)/(observer.samples[-1][0]-observer.samples[0][0])
            assert 8 <= rate <= 12, rate
            assert all(abs(v-0.5) < 1e-6 and abs(w-0.3) < 1e-6 for _, v, w in observer.samples)
            assert observer.count_publishers('/turtle1/cmd_vel') == 1
            after = observer.coordinates()
            assert math.hypot(after[0]-broken[0], after[1]-broken[1]) > 0.1
            print(f'PASS fix: {duration:.3f}s, {len(observer.samples)} messages, {rate:.3f} Hz, Twist=(0.5, 0.3)', flush=True)
            print(f'PASS motion: before={broken}; after={after}', flush=True)
            finish_patrol(patrol)
            observer.wait(lambda: observer.count_publishers('/turtle1/cmd_vel') == 0)
            observer.spin_for(2)
            resting = observer.coordinates()
            observer.spin_for(0.5)
            assert all(abs(a-b) < 1e-5 for a, b in zip(resting, observer.coordinates()))
            assert observer.pose.linear_velocity == observer.pose.angular_velocity == 0
            print(f'PASS SIGINT: patrol exited 0; no command publisher; watchdog stopped turtle at {resting}', flush=True)
            stop(simulator)
            assert simulator.returncode == 0
            observer.wait(lambda: 'turtlesim' not in observer.get_node_names())
            print('PASS PR03 live experiment', flush=True)
        except Exception:
            for _, path in children:
                print(f'Process {path.name}:\n{path.read_text()[-2500:]}', flush=True)
            raise
        finally:
            try:
                for child, _ in reversed(children):
                    stop(child)
            finally:
                observer.destroy_node()
                rclpy.try_shutdown()


if __name__ == '__main__':
    main()
