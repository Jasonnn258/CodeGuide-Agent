from task_065_lib.pages import page_count


def test_exact_multiple():
    assert page_count(100, 10) == 10


def test_multiple_pages():
    assert page_count(200, 10) == 20


def test_zero_items():
    assert page_count(0, 10) == 0
