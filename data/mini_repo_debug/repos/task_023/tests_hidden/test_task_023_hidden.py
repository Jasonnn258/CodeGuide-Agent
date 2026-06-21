from task_023_lib.cache import make_cache_key


def test_nested_params_are_stable():
    a = {"filters": {"color": "black", "sizes": ["M", "L"]}, "page": 1}
    b = {"page": 1, "filters": {"sizes": ["M", "L"], "color": "black"}}
    assert make_cache_key("search", a) == make_cache_key("search", b)


def test_name_is_part_of_key():
    params = {"id": 7}
    assert make_cache_key("product", params) != make_cache_key("seller", params)
