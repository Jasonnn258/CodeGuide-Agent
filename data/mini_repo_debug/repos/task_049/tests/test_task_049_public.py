from task_049_lib.config import is_enabled


def test_boolean_true():
    assert is_enabled('{"enabled": true}') is True


def test_boolean_false():
    assert is_enabled('{"enabled": false}') is False
