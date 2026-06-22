from task_053_lib.sorting import sort_names


def test_sorts_case_insensitively():
    assert sort_names(["Bob", "alice", "Charlie"]) == ["alice", "Bob", "Charlie"]


def test_mixed_case_stable():
    assert sort_names(["CAR", "apple", "banana"]) == ["apple", "banana", "CAR"]
