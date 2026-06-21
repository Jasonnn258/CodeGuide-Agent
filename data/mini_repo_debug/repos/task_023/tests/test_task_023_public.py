from task_023_lib.cache import make_cache_key


def test_different_params_do_not_collide():
    assert make_cache_key("search", {"q": "shoe"}) != make_cache_key("search", {"q": "bag"})


def test_same_params_have_same_key_even_if_order_differs():
    assert make_cache_key("search", {"q": "shoe", "page": 1}) == make_cache_key("search", {"page": 1, "q": "shoe"})
