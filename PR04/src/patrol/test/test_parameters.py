"""Validate pure selection, atomic updates, and live timer ownership."""

from patrol.control import choose_command, DEFAULTS, select_parameters
from patrol.patrol import Patrol
import pytest
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.parameter import Parameter


@pytest.mark.parametrize('name,value', [
    ('linear_speed', 0), ('linear_speed', 1), ('linear_speed', 0.7),
    ('turn_rate', -1), ('turn_rate', 1), ('turn_rate', 0),
    ('publish_hz', 1), ('publish_hz', 30), ('publish_hz', 5.0),
])
def test_valid_values_are_selected_without_mutation(name, value):
    current = dict(DEFAULTS)
    updates = {name: value}
    selected = select_parameters(current, updates)
    assert selected[name] == float(value)
    assert current == DEFAULTS
    assert updates == {name: value}
    assert selected is not current


@pytest.mark.parametrize('name,value', [
    ('publish_hz', 0.0), ('publish_hz', -1.0), ('publish_hz', 30.1),
    ('linear_speed', -0.1), ('linear_speed', 1.1),
    ('turn_rate', -1.1), ('turn_rate', 1.1),
] + [(name, value) for name in DEFAULTS
     for value in [float('nan'), float('inf'), float('-inf'), True, '5', None]])
def test_invalid_values_are_rejected_without_mutation(name, value):
    current = dict(DEFAULTS)
    with pytest.raises(ValueError, match=name):
        select_parameters(current, {name: value})
    assert current == DEFAULTS


def test_unknown_setting_is_rejected():
    with pytest.raises(ValueError, match='Unknown'):
        select_parameters(DEFAULTS, {'typo': 5.0})


def test_command_uses_both_active_speeds_and_stops_without_pose():
    assert choose_command(None, 0.8, -0.6) == (0.0, 0.0)
    assert choose_command(object(), 0.8, -0.6) == (0.8, -0.6)


@pytest.fixture
def node():
    rclpy.init()
    instance = Patrol()
    try:
        yield instance
    finally:
        instance.destroy_node()
        rclpy.try_shutdown()


def test_runtime_rejections_preserve_timer_and_active_state(node):
    original_timer = node.timer
    for name, value in [
        ('publish_hz', 0.0), ('publish_hz', -1.0),
        ('publish_hz', float('nan')), ('publish_hz', float('inf')),
        ('linear_speed', 2.0), ('turn_rate', -2.0),
    ]:
        result = node.set_parameters_atomically([Parameter(name, value=value)])
        assert not result.successful
        assert name in result.reason
        assert node.settings == DEFAULTS
        assert node.get_parameter(name).value == DEFAULTS[name]
        assert node.timer is original_timer
        assert not node.timer.is_canceled()
        assert list(node.timers) == [original_timer]


def test_frequency_changes_replace_exactly_one_timer(node):
    for hz in [5.0, 30.0, 1.0, 10.0, 5.0]:
        previous = node.timer
        result = node.set_parameters_atomically([Parameter('publish_hz', value=hz)])
        assert result.successful
        assert node.timer is not previous
        assert list(node.timers) == [node.timer]
        assert node.timer.timer_period_ns == int(1e9 / hz)
        assert not node.timer.is_canceled()
        assert node.settings['publish_hz'] == hz
        assert node.get_parameter('publish_hz').value == hz


def test_same_frequency_and_speed_updates_keep_timer(node):
    original = node.timer
    result = node.set_parameters_atomically([
        Parameter('publish_hz', value=10.0),
        Parameter('linear_speed', value=0.8),
        Parameter('turn_rate', value=-0.6),
    ])
    assert result.successful
    assert node.timer is original
    assert node.settings == {'linear_speed': 0.8, 'turn_rate': -0.6, 'publish_hz': 10.0}


def test_invalid_atomic_batch_cannot_partially_change_speeds(node):
    original = node.timer
    result = node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8),
        Parameter('publish_hz', value=0.0),
    ])
    assert not result.successful
    assert node.settings == DEFAULTS
    assert node.get_parameter('linear_speed').value == 0.5
    assert node.timer is original


def test_other_validator_can_veto_without_timer_side_effects(node):
    # Run the patrol validator first, then a second validator which rejects.
    node.remove_on_set_parameters_callback(node.validate_parameters)
    node.add_on_set_parameters_callback(
        lambda parameters: SetParametersResult(successful=False, reason='external veto'))
    node.add_on_set_parameters_callback(node.validate_parameters)
    original = node.timer
    result = node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])
    assert not result.successful
    assert node.timer is original
    assert node.settings == DEFAULTS
    assert node.get_parameter('publish_hz').value == 10.0
