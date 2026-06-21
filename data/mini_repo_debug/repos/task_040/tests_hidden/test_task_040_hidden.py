from task_040_lib.merge import merge_config


def test_nested_dicts_are_merged():
    result = merge_config({"db": {"host": "localhost", "port": 5432}}, {"db": {"port": 5433}})
    assert result == {"db": {"host": "localhost", "port": 5433}}


def test_defaults_are_not_mutated():
    defaults = {"db": {"host": "localhost", "port": 5432}}
    merge_config(defaults, {"db": {"port": 5433}})
    assert defaults == {"db": {"host": "localhost", "port": 5432}}
