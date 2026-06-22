from task_064_lib.query import build_query


def test_none_values_are_skipped():
    assert build_query(a=1, b=None) == "a=1"


def test_all_none_returns_empty():
    assert build_query(x=None, y=None) == ""
