from task_051_lib.parser import parse_int


def test_parses_integer_string():
    assert parse_int("42") == 42


def test_returns_none_for_garbage():
    assert parse_int("abc") is None
