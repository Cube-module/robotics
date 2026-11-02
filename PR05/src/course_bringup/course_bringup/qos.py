"""Construct explicit, compatible sensor profiles."""

from rclpy.qos import (
    DurabilityPolicy, HistoryPolicy, LivelinessPolicy, QoSProfile, ReliabilityPolicy,
)


def sensor_qos(reliability):
    """Validate the requested reliability and create an independent profile."""
    policies = {
        'reliable': ReliabilityPolicy.RELIABLE,
        'best_effort': ReliabilityPolicy.BEST_EFFORT,
    }
    if reliability not in policies:
        raise ValueError('reliability must be reliable or best_effort')
    return QoSProfile(
        reliability=policies[reliability],
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        durability=DurabilityPolicy.VOLATILE,
        liveliness=LivelinessPolicy.AUTOMATIC,
    )
