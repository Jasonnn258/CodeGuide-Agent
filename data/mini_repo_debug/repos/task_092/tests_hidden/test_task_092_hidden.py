from task_092_lib.bounds import clamp


def test_swapped_bounds_raise_value_error():
    try:
        clamp(5, 10, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for swapped bounds")


def test_equal_bounds_are_valid():
    assert clamp(7, 5, 5) == 5
