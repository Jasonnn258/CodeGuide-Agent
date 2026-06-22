from task_065_lib.pages import page_count


def test_partial_last_page_counts():
    assert page_count(21, 10) == 3


def test_one_over_boundary():
    assert page_count(11, 10) == 2


def test_less_than_page_size_counts_as_one():
    assert page_count(5, 10) == 1
