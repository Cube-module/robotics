"""Publish pose-driven velocity commands with validated runtime parameters."""

from geometry_msgs.msg import Twist
from patrol.control import choose_command, DEFAULTS, select_parameters
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


class Patrol(Node):
    """Keep the latest pose and publish velocity commands from a timer."""

    def __init__(self, **kwargs):
        """Create the subscription, relative publisher and timer."""
        super().__init__('patrol', **kwargs)
        for name, default in DEFAULTS.items():
            self.declare_parameter(
                name, default, ParameterDescriptor(dynamic_typing=True))
        self.settings = select_parameters(
            DEFAULTS, {name: self.get_parameter(name).value for name in DEFAULTS})

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
            1.0 / self.settings['publish_hz'],
            self.timer_callback
        )

        self.add_on_set_parameters_callback(self.validate_parameters)
        self.add_post_set_parameters_callback(self.apply_parameters)

    def parameter_candidate(self, parameters):
        """Select all requested patrol settings without changing active state."""
        return select_parameters(
            self.settings, {p.name: p.value for p in parameters if p.name in DEFAULTS})

    def validate_parameters(self, parameters):
        """Reject invalid batches before any parameter or timer is changed."""
        try:
            self.parameter_candidate(parameters)
        except ValueError as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def apply_parameters(self, parameters):
        """Apply an accepted batch and replace the timer only on frequency changes."""
        candidate = self.parameter_candidate(parameters)
        if candidate['publish_hz'] != self.settings['publish_hz']:
            period = 1.0 / candidate['publish_hz']
            self.timer.cancel()
            self.destroy_timer(self.timer)
            self.timer = self.create_timer(period, self.timer_callback)
        self.settings = candidate

    def pose_callback(self, msg):
        """Store the latest pose without modifying it."""
        self.pose = msg

    def timer_callback(self):
        """Publish zero before the first pose, then the patrol command."""
        command = Twist()

        command.linear.x, command.angular.z = choose_command(
            self.pose, self.settings['linear_speed'], self.settings['turn_rate'])

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
