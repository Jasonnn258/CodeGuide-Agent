from task_066_lib.whitespace import collapse_whitespace


def test_tabs_are_collapsed():
    assert collapse_whitespace("hello\t\tworld") == "hello world"


def test_mixed_whitespace_collapsed():
    assert collapse_whitespace("one \t two  \t  three") == "one two three"
