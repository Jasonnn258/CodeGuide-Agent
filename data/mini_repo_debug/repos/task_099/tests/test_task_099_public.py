from task_099_lib.password_check import is_strong_password


def test_strong_password():
    assert is_strong_password("Str0ng!Pass") is True


def test_too_short():
    assert is_strong_password("Ab1!") is False


def test_missing_digit():
    assert is_strong_password("Abcdefgh!") is False


def test_missing_uppercase():
    assert is_strong_password("abcdefgh1!") is False
