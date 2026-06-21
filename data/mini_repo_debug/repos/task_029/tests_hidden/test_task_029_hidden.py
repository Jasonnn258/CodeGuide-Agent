from task_029_lib.parser import ConfigError, parse_timeout


def test_non_numeric_timeout_raises_config_error():
    try:
        parse_timeout({"timeout": "soon"})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")


def test_non_positive_timeout_raises_config_error():
    try:
        parse_timeout({"timeout": 0})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")
