from task_099_lib.password_check import is_strong_password


def test_no_special_char_is_weak():
    assert is_strong_password("Password1") is False


def test_all_alphanumeric_is_weak():
    assert is_strong_password("Abcd1234") is False


def test_single_special_char_ok():
    assert is_strong_password("Abcd1234!") is True
