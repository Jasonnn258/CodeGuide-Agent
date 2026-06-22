from task_061_lib.version import parse_version


def test_stable_version():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_zero_version():
    assert parse_version("0.0.1") == (0, 0, 1)
