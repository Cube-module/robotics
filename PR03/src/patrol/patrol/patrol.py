"""Publish a fixed command at 10 Hz after receiving the first turtle pose."""

from geometry_msgs.msg import Twist
from patrol.control import choose_command
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


class Patrol(Node):
    """Keep the latest pose and publish velocity commands from a timer."""

    def __init__(self):
        """Create the subscription, relative publisher and timer."""
        super().__init__('patrol')

        self.pose = None

        self.pose_subscriber = self.create_subscription(
            Pose,
            '/turtle1/pose',
            self.pose_callback,
            10
        )

        self.cmd_publisher = self.create_publisher(
            Twist,
            'cmd_vel',
            10
        )

        self.timer = self.create_timer(
            0.1,
            self.timer_callback
        )

    def pose_callback(self, msg):
        """Store the latest pose without modifying it."""
        self.pose = msg

    def timer_callback(self):
        """Publish zero before the first pose, then the patrol command."""
        command = Twist()

        command.linear.x, command.angular.z = choose_command(self.pose)

        self.cmd_publisher.publish(command)


def main(args=None):
    """Run patrol and release ROS resources on SIGINT."""
    rclpy.init(args=args)

    node = Patrol()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
