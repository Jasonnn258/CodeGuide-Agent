from task_085_lib.wrap import wrap_text


def test_short_words_fit():
    assert wrap_text("hello world", 20) == ["hello world"]


def test_wraps_at_width():
    result = wrap_text("hello world foo", 10)
    assert len(result) == 2
    assert result[0] == "hello"
    assert result[1] == "world foo"


def test_empty_text():
    assert wrap_text("", 10) == []
