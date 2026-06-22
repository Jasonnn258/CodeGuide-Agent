from task_079_lib.email_check import is_valid_email


def test_at_sign_at_start_is_invalid():
    assert is_valid_email("@example.com") is False


def test_dot_before_at_is_rejected():
    assert is_valid_email("alice.smith@examplecom") is False


def test_dot_at_end_is_invalid():
    assert is_valid_email("alice@example.") is False


def test_dot_immediately_after_at_is_invalid():
    assert is_valid_email("alice@.com") is False
