from task_064_lib.query import build_query


def test_all_parameters_present():
    assert build_query(a=1, b=2) == "a=1&b=2"


def test_single_parameter():
    assert build_query(q="search") == "q=search"
