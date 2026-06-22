from task_092_lib.bounds import clamp


def test_value_within_range():
    assert clamp(5, 0, 10) == 5


def test_value_below_range():
    assert clamp(-5, 0, 10) == 0


def test_value_above_range():
    assert clamp(15, 0, 10) == 10


def test_value_at_lower_boundary():
    assert clamp(0, 0, 10) == 0
