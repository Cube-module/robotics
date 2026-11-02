"""Share clean signal handling between the two small experiment nodes."""

import rclpy
from rclpy.executors import ExternalShutdownException


def run(node_type, args=None):
    """Spin a node until SIGINT or context shutdown and release resources."""
    rclpy.init(args=args)
    node = None
    try:
        node = node_type()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
