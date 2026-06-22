from task_060_lib.config import merge_config


def test_deep_merge_preserves_sibling_keys():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"host": "prod-host"}}
    result = merge_config(base, override)
    assert result["db"]["host"] == "prod-host"
    assert result["db"]["port"] == 5432


def test_deep_merge_adds_nested_key():
    base = {"server": {"name": "main"}}
    override = {"server": {"timeout": 30}}
    result = merge_config(base, override)
    assert result["server"]["name"] == "main"
    assert result["server"]["timeout"] == 30
