from task_035_lib.roles import has_role


def test_exact_role_match():
    assert has_role(["admin", "viewer"], "admin") is True


def test_missing_role():
    assert has_role(["viewer"], "admin") is False
