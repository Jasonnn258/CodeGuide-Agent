from task_089_lib.settings import get_nested


def test_missing_top_level_key_returns_none():
    assert get_nested('{"a": 1}', "b") is None


def test_missing_nested_key_returns_none():
    assert get_nested('{"db": {"host": "localhost"}}', "db.port") is None


def test_deeply_missing_key_returns_none():
    assert get_nested('{"a": {"b": 1}}', "a.c.d") is None
