from task_045_lib.windows import take_window


def test_window_inside_list():
    assert take_window([1, 2, 3, 4], 1, 2) == [2, 3]


def test_rejects_overrun():
    assert take_window([1, 2, 3], 2, 2) == []
