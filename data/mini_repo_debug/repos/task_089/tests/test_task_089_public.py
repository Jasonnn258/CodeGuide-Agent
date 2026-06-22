from task_089_lib.settings import get_nested


def test_single_level():
    assert get_nested('{"host": "localhost"}', "host") == "localhost"


def test_nested_path():
    result = get_nested('{"db": {"host": "localhost"}}', "db.host")
    assert result == "localhost"


def test_numeric_value():
    assert get_nested('{"port": 5432}', "port") == 5432
