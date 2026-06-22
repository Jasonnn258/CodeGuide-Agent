from task_085_lib.wrap import wrap_text


def test_long_word_is_split():
    result = wrap_text("hello supercalifragilistic world", 10)
    assert "supercalif" in result
    assert "ragilistic" in result


def test_long_word_preserves_other_words():
    result = wrap_text("a verylongword b", 5)
    assert result[0] == "a"
    assert result[1] == "veryl"
    assert "b" in result[-1]
