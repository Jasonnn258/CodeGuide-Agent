from task_072_lib.math_utils import safe_percentage


def test_rounded_to_two_decimals():
    assert safe_percentage(1, 3) == 33.33


def test_rounded_up_at_boundary():
    assert safe_percentage(2, 3) == 66.67
