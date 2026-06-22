from task_060_lib.config import merge_config


def test_flat_merge_adds_new_key():
    base = {"host": "localhost"}
    override = {"port": 5432}
    result = merge_config(base, override)
    assert result == {"host": "localhost", "port": 5432}


def test_flat_merge_overwrites_existing_key():
    base = {"host": "localhost", "port": 8080}
    override = {"port": 5432}
    result = merge_config(base, override)
    assert result["port"] == 5432
