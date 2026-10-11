"""Проверки решения ПР03: решение по позе и настоящий обмен ROS."""
import time
from types import SimpleNamespace

from geometry_msgs.msg import Twist
from patrol.control import choose_command
from patrol.patrol import Patrol, Pose
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node


def test_no_pose_means_stop():
    assert choose_command(None) == (0.0, 0.0)


@pytest.mark.parametrize('x,y,theta', [(0.0, 0.0, 0.0), (5.5, 5.5, 1.2)])
def test_received_pose_allows_fixed_command_without_mutation(x, y, theta):
    pose = SimpleNamespace(x=x, y=y, theta=theta)
    assert choose_command(pose) == (0.5, 0.3)
    assert vars(pose) == {'x': x, 'y': y, 'theta': theta}


def test_subscription_updates_state_and_timer_uses_it():
    rclpy.init(args=['--ros-args', '-r', '__ns:=/pr03_test'])
    node = Patrol()
    observer = Node('observer')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(observer)
    messages = []
    observer.create_subscription(Twist, '/pr03_test/cmd_vel', messages.append, 10)
    publisher = observer.create_publisher(Pose, '/turtle1/pose', 10)

    def until(condition):
        deadline = time.monotonic() + 5.0
        while not condition() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
        assert condition(), 'Expected ROS event did not arrive'

    try:
        until(lambda: len(messages) >= 3)
        assert node.pose is None
        assert all(m.linear.x == m.angular.z == 0 for m in messages)
        until(lambda: publisher.get_subscription_count() == 1)
        publisher.publish(Pose(x=2.0, y=3.0))
        until(lambda: node.pose is not None)
        assert node.pose.x == 2.0
        until(lambda: any(m.linear.x == 0.5 and m.angular.z == 0.3 for m in messages))
        publisher.publish(Pose(x=7.0, y=4.0))
        until(lambda: node.pose.x == 7.0)
        assert node.pose.y == 4.0
        assert observer.count_publishers('/pr03_test/cmd_vel') == 1
        assert all(m.linear.y == m.linear.z == m.angular.x == m.angular.y == 0 for m in messages)
    finally:
        executor.shutdown()
        node.destroy_node()
        observer.destroy_node()
        rclpy.try_shutdown()
