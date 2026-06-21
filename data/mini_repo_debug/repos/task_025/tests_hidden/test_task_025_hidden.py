from task_025_lib.stats import moving_average


def test_empty_when_not_enough_values():
    assert moving_average([1], 2) == []


def test_invalid_window_raises():
    try:
        moving_average([1, 2, 3], 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
