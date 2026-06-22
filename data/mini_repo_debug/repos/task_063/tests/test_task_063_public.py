from task_063_lib.keys import make_cache_key


def test_different_values_produce_different_keys():
    assert make_cache_key("add", 1, 2) != make_cache_key("add", 1, 3)


def test_different_names_produce_different_keys():
    assert make_cache_key("add", 1, 2) != make_cache_key("sub", 1, 2)
