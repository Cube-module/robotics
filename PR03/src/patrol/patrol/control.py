"""Выбор (linear.x, angular.z) независимо от ROS."""


def choose_command(pose):
    """Стоять до первой позы, затем двигаться с фиксированной командой."""
    if pose is None:
        return 0.0, 0.0
    return 0.5, 0.3
