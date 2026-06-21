from task_032_lib.percent import percent_change


def test_zero_old_value_raises():
    try:
        percent_change(0, 5)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
