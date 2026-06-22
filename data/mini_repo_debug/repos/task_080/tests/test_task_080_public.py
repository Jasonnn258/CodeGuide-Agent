from task_080_lib.merge import merge_lists


def test_disjoint_lists():
    assert merge_lists([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_empty_second():
    assert merge_lists([1, 2], []) == [1, 2]


def test_both_empty():
    assert merge_lists([], []) == []
