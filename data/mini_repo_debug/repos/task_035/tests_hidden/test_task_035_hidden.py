from task_035_lib.roles import has_role


def test_case_insensitive_match():
    assert has_role(["Admin"], "admin") is True


def test_whitespace_is_ignored():
    assert has_role([" viewer "], "viewer") is True
