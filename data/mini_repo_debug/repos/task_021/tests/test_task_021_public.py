from task_021_lib.normalizer import normalize_label


def test_lowercase_and_strip():
    assert normalize_label("  Running Shoe  ") == "running shoe"


def test_simple_case_insensitive_match():
    assert normalize_label("HOODIE") == "hoodie"
