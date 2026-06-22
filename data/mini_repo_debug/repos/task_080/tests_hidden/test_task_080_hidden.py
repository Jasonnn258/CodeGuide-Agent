from task_080_lib.merge import merge_lists


def test_overlapping_lists_deduplicated():
    assert merge_lists([1, 2, 3], [2, 3, 4]) == [1, 2, 3, 4]


def test_first_already_contains_all():
    assert merge_lists(["a", "b", "c"], ["b"]) == ["a", "b", "c"]


def test_order_preserved_with_dedup():
    assert merge_lists([3, 1], [2, 1, 4]) == [3, 1, 2, 4]
