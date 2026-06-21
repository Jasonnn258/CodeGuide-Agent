from task_039_lib.usernames import is_valid_username


def test_rejects_digit_prefix():
    assert is_valid_username("1ada") is False


def test_rejects_symbols():
    assert is_valid_username("ada!") is False
