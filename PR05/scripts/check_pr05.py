#!/usr/bin/env python3
"""Run real PR05 experiments; keep commands, raw output, bags and assertions."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy
import yaml


TOPIC = '/robot_a/sensor_pose'


class Experiment:
    def __init__(self, output):
        self.output = output
        self.children = []
        self.commands = []
        self.observer = Node('pr05_verifier')
        self.result = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
                       'domain': os.environ.get('ROS_DOMAIN_ID', '0'), 'checks': {}}

    def wait(self, condition, seconds=12):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            rclpy.spin_once(self.observer, timeout_sec=0.05)
        assert condition(), 'Expected graph/log event did not arrive'

    def command(self, args, log, expected=0):
        command = shlex.join(args)
        self.commands.append(command)
        print('$ ' + command, flush=True)
        completed = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=25)
        with log.open('a') as stream:
            stream.write('$ ' + command + '\n' + completed.stdout)
            stream.write(f'\nexit_code={completed.returncode}\n\n')
        self.last_exit = completed.returncode
        assert expected is None or completed.returncode == expected, (command, completed.returncode,
                                                   completed.stdout)
        return completed.stdout

    def query(self, args, log, required):
        # A fresh CLI participant needs its own discovery even when our observer
        # already sees the graph. Preserve every attempt, including empty output.
        for seconds in (2, 4, 8):
            text = self.command(['ros2', *args, '--no-daemon', '--spin-time',
                                 str(seconds)], log, expected=None)
            missing = self.last_exit == 1 and (
                text.strip().startswith('Unknown topic')
                or text.strip().startswith('Unable to find node'))
            assert self.last_exit == 0 or missing, text
            if self.last_exit == 0 and all(item in text for item in required):
                return text
        raise AssertionError(f'CLI discovery failed: {args}; {text!r}')

    def start(self, args, filename):
        log = self.output / filename
        stream = log.open('w')
        command = shlex.join(args)
        self.commands.append(command)
        stream.write('$ ' + command + '\n')
        stream.flush()
        print('$ ' + command, flush=True)
        child = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        item = (child, stream, log)
        self.children.append(item)
        return item

    def stop(self, item):
        child, stream, log = item
        if stream.closed:
            return
        try:
            if child.poll() is None:
                if child.args[:2] == ['ros2', 'run']:
                    os.killpg(child.pid, signal.SIGINT)
                else:
                    child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    raise AssertionError(f'SIGINT failed: {child.args}')
        finally:
            stream.write(f'\nexit_code={child.returncode}\n')
            stream.close()
        text = log.read_text()
        assert child.returncode == 0, text
        assert 'Traceback' not in text and 'process has died' not in text, text

    def launch(self, reliability, name, record=False, namespace='robot_a'):
        return self.start([
            'ros2', 'launch', 'course_bringup', 'patrol.launch.py',
            'namespace:=' + namespace, 'subscriber_reliability:=' + reliability,
            'record:=' + str(record).lower(),
            'bag_dir:=' + str(self.output / name),
        ], name + '.log')

    def publishers(self, topic=TOPIC):
        return self.observer.get_publishers_info_by_topic(topic)

    def graph_ready(self, reliability, namespace='/robot_a'):
        topic = namespace + '/sensor_pose'
        publishers = self.publishers(topic)
        subscribers = self.observer.get_subscriptions_info_by_topic(topic)
        return (len(publishers) == 1
                and publishers[0].node_name == 'pose_relay'
                and publishers[0].node_namespace == namespace
                and publishers[0].qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
                and any(s.node_name == 'pose_subscriber'
                        and s.node_namespace == namespace
                        and s.qos_profile.reliability == reliability for s in subscribers))

    def echo(self, reliability, log, expected=0):
        text = self.command([
            'timeout', '3s', 'ros2', 'topic', 'echo', TOPIC, 'turtlesim/msg/Pose',
            '--qos-reliability', reliability, '--once',
        ], log, expected)
        if expected == 0:
            assert all(field + ':' in text for field in ('x', 'y', 'theta'))
        else:
            assert 'x:' not in text
        return text

    def inspect(self, log):
        nodes = self.query(['node', 'list'], log, ['/turtlesim', '/robot_a/pose_subscriber'])
        assert nodes.splitlines().count('/turtlesim') == 1, nodes
        for node in ('patrol', 'pose_relay', 'pose_subscriber'):
            assert '/robot_a/' + node in nodes, nodes
        topics = self.query(['topic', 'list'], log, [TOPIC])
        assert TOPIC in topics.splitlines(), topics
        info = self.query(['topic', 'info', TOPIC, '--verbose'], log, ['pose_relay', 'pose_subscriber'])
        assert 'BEST_EFFORT' in info
        patrol = self.query(['node', 'info', '/robot_a/patrol'], log, ['/turtle1/cmd_vel'])
        assert '/turtle1/cmd_vel: geometry_msgs/msg/Twist' in patrol
        assert '/turtle1/pose: turtlesim/msg/Pose' in patrol
        assert '/robot_a/cmd_vel:' not in patrol

    def check_bag(self, path):
        metadata = yaml.safe_load((path / 'metadata.yaml').read_text())
        info = metadata['rosbag2_bagfile_information']
        assert info['storage_identifier'] == 'mcap'
        assert info['message_count'] > 100, info
        topics = info['topics_with_message_count']
        assert len(topics) == 1
        assert topics[0]['topic_metadata']['name'] == TOPIC
        assert topics[0]['topic_metadata']['type'] == 'turtlesim/msg/Pose'
        return info['message_count']

    def run(self):
        before = self.output / 'qos-before.txt'
        after = self.output / 'qos-after.txt'
        assert not self.publishers(), 'An existing publisher would contaminate this experiment'
        assert not self.observer.count_publishers('/turtle1/pose')

        defect = self.launch('reliable', 'defect')
        self.wait(lambda: self.graph_ready(ReliabilityPolicy.RELIABLE))
        self.inspect(before)
        self.echo('reliable', before, expected=124)
        text = defect[2].read_text()
        assert 'Received poses: 0' in text
        assert not re.search(r'Received poses: [1-9]', text)
        assert not (self.output / 'defect').exists(), 'record=false created a bag'
        self.stop(defect)
        with before.open('a') as stream:
            stream.write('=== Launch log: incompatible subscriber ===\n')
            stream.write(defect[2].read_text())
        self.wait(lambda: not self.publishers())
        self.result['checks']['defect_reproduced'] = True
        print('PASS: visible topic, RELIABLE subscriber received zero; echo exit 124', flush=True)

        fixed = self.launch('best_effort', 'fixed')
        self.wait(lambda: self.graph_ready(ReliabilityPolicy.BEST_EFFORT))
        self.inspect(after)
        self.echo('best_effort', after)
        self.wait(lambda: re.search(r'Received poses: [1-9]', fixed[2].read_text()))
        assert not (self.output / 'fixed').exists(), 'record=false created a bag'
        recorder = self.start(['ros2', 'bag', 'record', '-s', 'mcap', '-o',
                               str(self.output / 'bag'), '--topics', TOPIC], 'record.log')
        self.wait(lambda: 'Subscribed to topic' in recorder[2].read_text())
        time.sleep(18)
        self.stop(recorder)
        self.result['bag_messages'] = self.check_bag(self.output / 'bag')
        self.command(['ros2', 'bag', 'info', str(self.output / 'bag')], after)
        shutil.copyfile(self.output / 'bag/metadata.yaml', self.output / 'bag-metadata.yaml')
        self.stop(fixed)
        with after.open('a') as stream:
            stream.write('=== Launch log: live compatible subscriber ===\n')
            stream.write(fixed[2].read_text())
            stream.write('=== Replay: live source stopped ===\n')
        self.wait(lambda: not self.publishers()
                  and not self.observer.count_publishers('/turtle1/pose'))
        self.result['checks']['defect_fixed'] = True
        print('PASS: live BEST_EFFORT messages and nonempty MCAP; live source stopped', flush=True)

        nodes = self.query(['node', 'list'], after, ['pr05_verifier'])
        assert 'pose_relay' not in nodes and 'turtlesim' not in nodes, nodes
        subscriber = self.start([
            'ros2', 'run', 'course_bringup', 'pose_subscriber', '--ros-args',
            '-r', '__ns:=/robot_a', '-p', 'subscriber_reliability:=best_effort',
        ], 'replay-subscriber.log')
        self.wait(lambda: any(s.node_name == 'pose_subscriber' for s in
                             self.observer.get_subscriptions_info_by_topic(TOPIC)))
        player = self.start(['ros2', 'bag', 'play', str(self.output / 'bag'),
                             '--qos-profile-overrides-path', 'config/qos-overrides.yaml'],
                            'replay.log')
        self.wait(lambda: len(self.publishers()) == 1
                  and self.publishers()[0].node_name.startswith('rosbag2_player'))
        publishers = self.publishers()
        assert publishers[0].node_name.startswith('rosbag2_player'), publishers
        assert publishers[0].qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
        self.query(['topic', 'info', TOPIC, '--verbose'], after, ['rosbag2_player'])
        self.echo('best_effort', after)
        self.wait(lambda: re.search(r'Received poses: [1-9]', subscriber[2].read_text()))
        player[0].wait(timeout=25)
        self.stop(player)
        self.stop(subscriber)
        with after.open('a') as stream:
            stream.write('=== Replay subscriber log ===\n')
            stream.write(subscriber[2].read_text())
        self.wait(lambda: not self.publishers())
        self.result['checks']['replay_verified'] = True
        print('PASS: replay only publisher, override BEST_EFFORT, subscriber received poses', flush=True)

        launch_record = self.launch('best_effort', 'launch-bag', record=True)
        self.wait(lambda: self.graph_ready(ReliabilityPolicy.BEST_EFFORT))
        self.wait(lambda: 'Subscribed to topic' in launch_record[2].read_text())
        time.sleep(4)
        self.stop(launch_record)
        self.result['launch_bag_messages'] = self.check_bag(self.output / 'launch-bag')
        self.command(['ros2', 'bag', 'info', str(self.output / 'launch-bag')], after)
        self.wait(lambda: not self.publishers())
        self.result['checks']['conditional_recording'] = True

        alternate = self.launch('best_effort', 'alternate', namespace='robot_b')
        self.wait(lambda: self.graph_ready(ReliabilityPolicy.BEST_EFFORT, '/robot_b'))
        assert not self.publishers(), 'Namespace argument was ignored'
        self.stop(alternate)
        self.wait(lambda: not self.publishers('/robot_b/sensor_pose'))
        self.result['checks']['namespace_and_remap'] = True
        self.result['checks']['clean_shutdown'] = True
        self.result['commands'] = self.commands
        self.result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        (self.output / 'runtime.json').write_text(json.dumps(self.result, indent=2) + '\n')
        print(json.dumps(self.result, indent=2), flush=True)

    def close(self):
        errors = []
        for child in reversed(self.children):
            try:
                self.stop(child)
            except Exception as error:
                errors.append(str(error))
        self.observer.destroy_node()
        if errors:
            raise AssertionError('\n'.join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New directory; existing evidence is never overwritten')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rclpy.init()
    experiment = Experiment(args.output)
    try:
        experiment.run()
    finally:
        try:
            experiment.close()
        finally:
            rclpy.try_shutdown()


if __name__ == '__main__':
    main()
