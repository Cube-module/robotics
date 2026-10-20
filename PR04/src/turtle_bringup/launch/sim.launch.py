"""Launch the turtlesim node."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Create the simulator launch description."""
    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
        )
    ])
