from task_029_lib.parser import ConfigError, parse_timeout


def test_valid_timeout_string():
    assert parse_timeout({"timeout": "30"}) == 30


def test_missing_timeout_raises_config_error():
    try:
        parse_timeout({})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")
