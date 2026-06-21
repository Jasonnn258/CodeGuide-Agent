from task_025_lib.stats import moving_average


def test_includes_final_window():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_window_equal_length():
    assert moving_average([2, 4, 6], 3) == [4.0]


def test_not_enough_values_returns_empty_list():
    assert moving_average([1], 2) == []
