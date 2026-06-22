from task_079_lib.email_check import is_valid_email


def test_valid_email():
    assert is_valid_email("alice@example.com") is True


def test_no_at_sign():
    assert is_valid_email("aliceexample.com") is False


def test_no_dot():
    assert is_valid_email("alice@example") is False
