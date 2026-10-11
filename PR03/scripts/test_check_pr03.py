"""Регрессии CI: позднее discovery, неполный граф и явные ошибки CLI."""
import subprocess
import sys
import time

import pytest

import check_pr03


def test_cli_discovers_topic_that_appears_after_first_snapshot():
    # Real ROS participant: the topic does not exist during the first 2 s query.
    child = subprocess.Popen([sys.executable, '-c', '''
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
time.sleep(5)
rclpy.init()
node = Node('late_discovery_fixture')
publisher = node.create_publisher(Twist, '/pr03_late_discovery', 10)
rclpy.spin(node)
'''], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert check_pr03.cli('topic', 'type', '/pr03_late_discovery').strip() == 'geometry_msgs/msg/Twist'
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_cli_waits_for_complete_endpoint_counts(monkeypatch):
    replies = iter([
        (1, '', "Unknown topic '/test'\n"),
        (0, 'Publisher count: 1\nSubscription count: 10\n', ''),
        (0, 'Publisher count: 1\nSubscription count: 1\n', ''),
    ])
    def run(command, **kwargs):
        code, out, err = next(replies)
        return subprocess.CompletedProcess(command, code, out, err)
    monkeypatch.setattr(check_pr03.subprocess, 'run', run)
    output = check_pr03.cli('topic', 'info', '/test', expected_lines=(
        'Publisher count: 1', 'Subscription count: 1'))
    assert output.splitlines() == ['Publisher count: 1', 'Subscription count: 1']


@pytest.mark.parametrize('code,error', [
    (2, 'unrecognized arguments: --bad'),
    (1, 'failed to initialize rcl'),
])
def test_cli_does_not_retry_invalid_command(monkeypatch, code, error):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, code, '', error)
    monkeypatch.setattr(check_pr03.subprocess, 'run', run)
    with pytest.raises(AssertionError, match=f'exit={code}.*{error}'):
        check_pr03.cli('topic', 'type', '/test')


def test_cli_missing_topic_has_bounded_wait_and_diagnostics():
    start = time.monotonic()
    with pytest.raises(AssertionError, match='/pr03_never_exists.*deadline'):
        check_pr03.cli('topic', 'type', '/pr03_never_exists', seconds=3)
    assert time.monotonic() - start < 6
