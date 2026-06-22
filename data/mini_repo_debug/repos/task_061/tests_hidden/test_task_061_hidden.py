from task_061_lib.version import parse_version


def test_prerelease_suffix_is_stripped():
    assert parse_version("1.2.3-beta") == (1, 2, 3)


def test_rc_suffix_is_stripped():
    assert parse_version("2.0.0-rc1") == (2, 0, 0)
