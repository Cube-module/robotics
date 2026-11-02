"""Observe sensor poses using a startup-selectable reliability policy."""

from course_bringup.qos import sensor_qos
from course_bringup.runtime import run
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseSubscriber(Node):
    """Count received poses and periodically report the actual latest pose."""

    def __init__(self):
        """Select reliability before creating the subscription."""
        super().__init__('pose_subscriber')
        self.declare_parameter(
            'subscriber_reliability', 'best_effort',
            ParameterDescriptor(read_only=True))
        reliability = self.get_parameter('subscriber_reliability').value
        self.count = 0
        self.latest = None
        self.subscription = self.create_subscription(
            Pose, 'sensor_pose', self.receive, sensor_qos(reliability))
        self.timer = self.create_timer(1.0, self.report)
        self.get_logger().info(f'Subscribing to sensor_pose: {reliability}')

    def receive(self, message):
        """Keep the real receive count and most recent pose."""
        self.count += 1
        self.latest = message

    def report(self):
        """Log once per second, including a visible zero in the defect case."""
        detail = '' if self.latest is None else (
            f' x={self.latest.x:.3f} y={self.latest.y:.3f}'
            f' theta={self.latest.theta:.3f}')
        self.get_logger().info(f'Received poses: {self.count}{detail}')


def main(args=None):
    """Run the configurable subscriber."""
    run(PoseSubscriber, args)
