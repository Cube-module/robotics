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
from rclpy.executors import SingleThreadedExecutor
from patrol.patrol import Pose


class Observer(Node):
    def __init__(self):
        super().__init__('pr03_observer')
        self.pose = None
        self.samples = []
        self.source_samples = []
        self._observer_executor = SingleThreadedExecutor()
        self._observer_executor.add_node(self)
        self.create_subscription(Pose, '/turtle1/pose', self.receive_pose, 10)

    def receive_pose(self, message):
        self.pose = message

    def receive_command(self, message, info):
        self.samples.append((time.monotonic(), message.linear.x, message.angular.z))
        self.source_samples.append(info['source_timestamp'])

    def wait(self, predicate, seconds=12):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            self._observer_executor.spin_once(timeout_sec=0.05)
        assert predicate(), 'Expected event did not arrive before timeout'

    def spin_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self._observer_executor.spin_once(timeout_sec=0.05)

    def destroy_node(self):
        self._observer_executor.shutdown()
        return super().destroy_node()

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
