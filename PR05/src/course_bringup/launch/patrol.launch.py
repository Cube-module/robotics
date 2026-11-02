"""Start one global simulator and namespaced patrol/QoS nodes."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Declare public arguments and conditionally record the resolved topic."""
    namespace = LaunchConfiguration('namespace')
    record = LaunchConfiguration('record')
    bag_dir = LaunchConfiguration('bag_dir')
    reliability = LaunchConfiguration('subscriber_reliability')
    topic = PathJoinSubstitution(['/', namespace, 'sensor_pose'])
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        DeclareLaunchArgument('record', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('bag_dir', default_value='evidence/pr05/launch-bag'),
        DeclareLaunchArgument(
            'subscriber_reliability', default_value='best_effort',
            choices=['reliable', 'best_effort']),
        Node(package='turtlesim', executable='turtlesim_node',
             name='turtlesim', namespace='/', output='screen'),
        Node(package='patrol', executable='patrol', namespace=namespace,
             remappings=[('cmd_vel', '/turtle1/cmd_vel')], output='screen'),
        Node(package='course_bringup', executable='pose_relay',
             namespace=namespace, output='screen'),
        Node(package='course_bringup', executable='pose_subscriber',
             namespace=namespace, output='screen', parameters=[{
                 'subscriber_reliability': ParameterValue(reliability, value_type=str),
             }]),
        ExecuteProcess(
            cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir,
                 '--topics', topic],
            condition=IfCondition(record), output='screen'),
    ])
