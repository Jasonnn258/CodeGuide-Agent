from task_066_lib.whitespace import collapse_whitespace


def test_single_spaces_unchanged():
    assert collapse_whitespace("hello world") == "hello world"


def test_multiple_spaces_collapsed():
    assert collapse_whitespace("hello   world") == "hello world"


def test_leading_trailing_stripped():
    assert collapse_whitespace("  hello  ") == "hello"
