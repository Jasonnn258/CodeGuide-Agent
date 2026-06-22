from task_072_lib.math_utils import safe_percentage


def test_exact_percentage():
    assert safe_percentage(25, 100) == 25.0


def test_zero_whole_is_safe():
    assert safe_percentage(25, 0) == 0.0


def test_fifty_percent():
    assert safe_percentage(1, 2) == 50.0
