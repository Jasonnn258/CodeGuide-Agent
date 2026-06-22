from task_053_lib.sorting import sort_names


def test_sorts_lowercase_names():
    assert sort_names(["bob", "alice", "charlie"]) == ["alice", "bob", "charlie"]


def test_sorts_numeric_prefixes():
    assert sort_names(["v2", "v1", "v10"]) == ["v1", "v10", "v2"]
