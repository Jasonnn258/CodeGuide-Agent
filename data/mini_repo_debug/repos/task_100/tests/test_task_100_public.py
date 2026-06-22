from task_100_lib.layered import layered_merge


def test_lists_are_concatenated():
    a = {"tags": ["a", "b"]}
    b = {"tags": ["c"]}
    result = layered_merge(a, b)
    assert result["tags"] == ["a", "b", "c"]


def test_scalar_is_overwritten():
    result = layered_merge({"x": 1}, {"x": 2})
    assert result["x"] == 2


def test_new_key_is_added():
    result = layered_merge({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}
