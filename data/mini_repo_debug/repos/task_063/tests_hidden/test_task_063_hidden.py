from task_063_lib.keys import make_cache_key


def test_int_vs_float_produce_different_keys():
    assert make_cache_key("f", 1) != make_cache_key("f", 1.0)


def test_string_vs_int_produce_different_keys():
    assert make_cache_key("f", "42") != make_cache_key("f", 42)
