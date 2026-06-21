from task_021_lib.normalizer import normalize_label


def test_collapses_repeated_spaces():
    assert normalize_label("Running    Shoe") == "running shoe"


def test_removes_punctuation():
    assert normalize_label("Men's Jacket!!!") == "mens jacket"
