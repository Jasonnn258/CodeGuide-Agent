from task_031_lib.ports import parse_port


def test_default_port():
    assert parse_port({}) == 8080


def test_string_port():
    assert parse_port({"port": "9000"}) == 9000
