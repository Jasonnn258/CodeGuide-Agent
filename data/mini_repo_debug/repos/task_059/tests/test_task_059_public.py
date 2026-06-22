from task_059_lib.validators import is_valid_username


def test_valid_username_accepted():
    assert is_valid_username("alice") is True


def test_too_short_username_rejected():
    assert is_valid_username("ab") is False


def test_special_characters_rejected():
    assert is_valid_username("bad!") is False
