from task_076_lib.validator import is_positive


def test_is_positive_true():
    assert is_positive(5) is True


def test_is_positive_false():
    assert is_positive(-1) is False
    assert is_positive(0) is False
