from task_049_lib.config import is_enabled


def test_string_false_is_disabled():
    assert is_enabled('{"enabled": "false"}') is False


def test_string_yes_is_enabled():
    assert is_enabled('{"enabled": "yes"}') is True
