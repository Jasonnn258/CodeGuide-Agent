from task_037_lib.batches import add_batch_item


def test_default_batch_is_not_shared():
    assert add_batch_item("a") == ["a"]
    assert add_batch_item("b") == ["b"]
