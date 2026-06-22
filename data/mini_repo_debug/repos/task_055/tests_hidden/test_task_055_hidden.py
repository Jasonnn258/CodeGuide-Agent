from task_055_lib.tags import normalize_tag


def test_strips_leading_whitespace():
    assert normalize_tag("  Go") == "go"


def test_strips_trailing_whitespace():
    assert normalize_tag("Rust  ") == "rust"


def test_strips_both_sides():
    assert normalize_tag("  Python  ") == "python"
