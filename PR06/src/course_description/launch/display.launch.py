"""Expand the model and start its sole TF publisher with optional visualization."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import yaml


def generate_launch_description():
    share = Path(get_package_share_directory('course_description'))
    dimensions = yaml.safe_load((share / 'config/dimensions.yaml').read_text())
    names = ('wheelbase', 'track', 'wheel_radius')
    command = [FindExecutable(name='xacro'), ' ', str(share / 'urdf/vehicle.urdf.xacro')]
    for name in names:
        command.extend([' ' + name + ':=', LaunchConfiguration(name)])
    return LaunchDescription([
        *[DeclareLaunchArgument(name, default_value=str(dimensions[name])) for name in names],
        DeclareLaunchArgument('rviz', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('demo_joints', default_value='false', choices=['true', 'false']),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', output='screen',
             parameters=[{'robot_description': ParameterValue(Command(command), value_type=str)}]),
        Node(package='course_description', executable='demo_joint_states.py',
             name='demo_joint_states', output='screen',
             condition=IfCondition(LaunchConfiguration('demo_joints'))),
        Node(package='rviz2', executable='rviz2', name='rviz2', output='screen',
             arguments=['-d', str(share / 'rviz/vehicle.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
