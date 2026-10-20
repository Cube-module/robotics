"""Регрессии CI: позднее discovery, неполный граф и явные ошибки CLI."""
import subprocess
import sys
import time

import pytest

import ros_support as check_pr03


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
publisher = node.create_publisher(Twist, '/pr04_late_discovery', 10)
rclpy.spin(node)
'''], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert check_pr03.cli('topic', 'type', '/pr04_late_discovery').strip() == 'geometry_msgs/msg/Twist'
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
    with pytest.raises(AssertionError, match='/pr04_never_exists.*deadline'):
        check_pr03.cli('topic', 'type', '/pr04_never_exists', seconds=3)
    assert time.monotonic() - start < 6


def test_observer_keeps_twist_stream_while_pose_callbacks_are_busy():
    import rclpy
    from geometry_msgs.msg import Twist
    from patrol.patrol import Pose
    from check_pr04 import measure

    rclpy.init()
    observer = check_pr03.Observer()
    try:
        pose_pub = observer.create_publisher(Pose, '/turtle1/pose', 10)
        twist_pub = observer.create_publisher(Twist, '/pr04_measurement_test', 10)
        observer.create_subscription(
            Twist, '/pr04_measurement_test', observer.receive_command, 10)
        observer.create_timer(0.016, lambda: pose_pub.publish(Pose(x=3.0)))
        observer.create_timer(0.1, lambda: twist_pub.publish(Twist()))
        observer.wait(lambda: len(observer.samples) >= 5 and observer.pose is not None)
        result = measure(observer, 10.0, seconds=3.0)
        assert observer.pose.x == 3.0
        assert 8.0 <= result['source_hz'] <= 12.0
    finally:
        observer.destroy_node()
        rclpy.try_shutdown()
