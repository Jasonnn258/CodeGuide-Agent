from task_043_lib.cache import make_cache_key


def test_args_and_kwargs_are_both_preserved():
    assert make_cache_key("load", args=("users",), kwargs={"limit": 10}) != make_cache_key(
        "load", args=("users",), kwargs={"limit": 20}
    )
