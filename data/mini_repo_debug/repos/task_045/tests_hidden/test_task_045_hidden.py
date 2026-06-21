from task_045_lib.windows import take_window


def test_exact_end_boundary_is_allowed():
    assert take_window([1, 2, 3], 1, 2) == [2, 3]
