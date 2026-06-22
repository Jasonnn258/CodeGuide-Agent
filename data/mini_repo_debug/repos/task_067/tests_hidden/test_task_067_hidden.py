from task_067_lib.frequencies import word_freq


def test_input_list_is_preserved():
    words = ["x", "y", "x", "z"]
    word_freq(words)
    assert words == ["x", "y", "x", "z"]


def test_input_order_is_preserved():
    words = ["c", "a", "b"]
    word_freq(words)
    assert words == ["c", "a", "b"]
