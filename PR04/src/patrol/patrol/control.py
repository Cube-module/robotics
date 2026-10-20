"""Choose commands and validate patrol settings independently of ROS."""

import math

DEFAULTS = {'linear_speed': 0.5, 'turn_rate': 0.3, 'publish_hz': 10.0}
LIMITS = {'linear_speed': (0.0, 1.0), 'turn_rate': (-1.0, 1.0), 'publish_hz': (1.0, 30.0)}


def select_parameters(current, updates):
    """Return a validated copy without modifying either input mapping."""
    unknown = set(updates) - set(DEFAULTS)
    if unknown:
        raise ValueError(f'Unknown patrol parameters: {sorted(unknown)}')
    candidate = {**current, **updates}
    for name, (lower, upper) in LIMITS.items():
        value = candidate[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{name} must be a finite number in [{lower}, {upper}]')
        if not lower <= value <= upper or not math.isfinite(value):
            raise ValueError(f'{name} must be finite and in [{lower}, {upper}]')
        candidate[name] = float(value)
    return candidate


def choose_command(pose, linear_speed=0.5, turn_rate=0.3):
    """Stand still until a pose arrives, then use the active speeds."""
    if pose is None:
        return 0.0, 0.0
    return linear_speed, turn_rate
