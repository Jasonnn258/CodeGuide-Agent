from task_031_lib.ports import ConfigError, parse_port


def test_non_numeric_port_raises_config_error():
    try:
        parse_port({"port": "soon"})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")


def test_out_of_range_port_raises_config_error():
    try:
        parse_port({"port": 70000})
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError")
