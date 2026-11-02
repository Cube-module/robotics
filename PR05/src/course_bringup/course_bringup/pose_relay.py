"""Relay the global turtlesim pose with BEST_EFFORT reliability."""

from course_bringup.qos import sensor_qos
from course_bringup.runtime import run
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseRelay(Node):
    """Forward each Pose unchanged to the relative sensor_pose topic."""

    def __init__(self):
        """Connect the global source and namespaced sensor publisher."""
        super().__init__('pose_relay')
        self.publisher = self.create_publisher(
            Pose, 'sensor_pose', sensor_qos('best_effort'))
        self.subscription = self.create_subscription(
            Pose, '/turtle1/pose', self.publisher.publish, 10)
        self.get_logger().info('Relaying /turtle1/pose to sensor_pose: BEST_EFFORT')


def main(args=None):
    """Run the relay."""
    run(PoseRelay, args)
