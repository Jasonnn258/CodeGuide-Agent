from task_086_lib.unicode_utils import strip_accents


def test_plain_ascii_unchanged():
    assert strip_accents("hello") == "hello"


def test_accented_e_removed():
    assert strip_accents("caf\u00e9") == "cafe"
