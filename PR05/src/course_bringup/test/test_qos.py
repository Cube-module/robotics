"""Check policy compatibility without starting a ROS graph."""

from course_bringup.qos import sensor_qos
import pytest
from rclpy.qos import (
    DurabilityPolicy, HistoryPolicy, qos_check_compatible,
    QoSCompatibility, ReliabilityPolicy,
)


@pytest.mark.parametrize('name,policy', [
    ('reliable', ReliabilityPolicy.RELIABLE),
    ('best_effort', ReliabilityPolicy.BEST_EFFORT),
])
def test_explicit_profile(name, policy):
    profile = sensor_qos(name)
    assert profile.reliability == policy
    assert profile.history == HistoryPolicy.KEEP_LAST
    assert profile.depth == 10
    assert profile.durability == DurabilityPolicy.VOLATILE


@pytest.mark.parametrize('value', ['', 'BEST_EFFORT', 'typo', None])
def test_invalid_reliability(value):
    with pytest.raises(ValueError, match='reliability'):
        sensor_qos(value)


def test_requested_reliability_reproduces_and_fixes_incompatibility():
    publisher = sensor_qos('best_effort')
    incompatible = qos_check_compatible(publisher, sensor_qos('reliable'))
    compatible = qos_check_compatible(publisher, sensor_qos('best_effort'))
    assert incompatible[0] == QoSCompatibility.ERROR
    assert compatible[0] == QoSCompatibility.OK


def test_profiles_do_not_share_mutable_state():
    first = sensor_qos('best_effort')
    first.depth = 1
    assert sensor_qos('best_effort').depth == 10
