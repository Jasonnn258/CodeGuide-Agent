from task_024_lib.tags import add_tag


def test_does_not_mutate_caller_list():
    original = ["shoe"]
    result = add_tag("new", original)
    assert result == ["shoe", "new"]
    assert original == ["shoe"]


def test_empty_explicit_list_is_not_reused():
    tags = []
    assert add_tag("a", tags) == ["a"]
    assert tags == []
