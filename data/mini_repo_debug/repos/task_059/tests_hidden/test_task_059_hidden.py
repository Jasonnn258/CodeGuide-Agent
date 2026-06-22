from task_059_lib.validators import is_valid_username


def test_trims_leading_whitespace():
    assert is_valid_username("  alice") is True


def test_trims_trailing_whitespace():
    assert is_valid_username("bob  ") is True


def test_whitespace_only_is_rejected():
    assert is_valid_username("   ") is False
