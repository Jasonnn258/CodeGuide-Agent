from task_039_lib.usernames import is_valid_username


def test_rejects_too_short_name():
    assert is_valid_username("ab") is False


def test_accepts_normal_name():
    assert is_valid_username("ada_1") is True
