from task_043_lib.cache import make_cache_key


def test_kwargs_affect_cache_key():
    assert make_cache_key("load", kwargs={"page": 1}) != make_cache_key("load", kwargs={"page": 2})


def test_kwargs_order_is_stable():
    assert make_cache_key("load", kwargs={"a": 1, "b": 2}) == make_cache_key("load", kwargs={"b": 2, "a": 1})
