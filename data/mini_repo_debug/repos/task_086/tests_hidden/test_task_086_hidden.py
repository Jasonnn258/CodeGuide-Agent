from task_086_lib.unicode_utils import strip_accents


def test_tilde_is_removed():
    assert strip_accents("se\u00f1or") == "senor"


def test_circumflex_is_removed():
    assert strip_accents("\u00eatre") == "etre"


def test_multiple_accents_in_one_word():
    assert strip_accents("\u00e1\u00e9\u00ed\u00f3\u00fa") == "aeiou"
