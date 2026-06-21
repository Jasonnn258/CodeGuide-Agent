from task_037_lib.batches import add_batch_item


def test_caller_list_is_not_mutated():
    original = ["a"]
    result = add_batch_item("b", original)
    assert result == ["a", "b"]
    assert original == ["a"]
