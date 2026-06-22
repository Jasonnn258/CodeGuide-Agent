from task_100_lib.layered import layered_merge


def test_nested_dicts_are_deep_merged():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"host": "prod.example.com"}}
    result = layered_merge(base, override)
    assert result["db"]["host"] == "prod.example.com"
    assert result["db"]["port"] == 5432


def test_deep_nested_dicts():
    a = {"a": {"b": {"x": 1}}}
    b = {"a": {"b": {"y": 2}}}
    result = layered_merge(a, b)
    assert result["a"]["b"]["x"] == 1
    assert result["a"]["b"]["y"] == 2
