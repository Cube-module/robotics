#!/usr/bin/env python3
"""Publish zero joint positions for visualization only; never publish TF."""
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState


class DemoJointStates(Node):
    def __init__(self):
        super().__init__('demo_joint_states')
        self.publisher = self.create_publisher(JointState, 'joint_states', 10)
        self.timer = self.create_timer(0.1, self.publish)

    def publish(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ['front_left_steering_joint', 'front_right_steering_joint',
                    'front_left_wheel_joint', 'front_right_wheel_joint',
                    'rear_left_wheel_joint', 'rear_right_wheel_joint']
        msg.position = [0.0] * len(msg.name)
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = DemoJointStates()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
