from task_055_lib.tags import normalize_tag


def test_lowercases_uppercase():
    assert normalize_tag("Python") == "python"


def test_preserves_lowercase():
    assert normalize_tag("rust") == "rust"
