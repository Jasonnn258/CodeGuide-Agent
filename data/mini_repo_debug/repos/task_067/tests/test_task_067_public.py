from task_067_lib.frequencies import word_freq


def test_counts_correctly():
    assert word_freq(["a", "b", "a"]) == {"a": 2, "b": 1}


def test_empty_list():
    assert word_freq([]) == {}
