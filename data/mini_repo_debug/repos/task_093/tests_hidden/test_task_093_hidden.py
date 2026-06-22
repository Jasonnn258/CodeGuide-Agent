from task_093_lib.matchers import filter_by_prefix


def test_case_insensitive_match():
    result = filter_by_prefix(["Apple", "apply", "banana"], "app", case_sensitive=False)
    assert result == ["Apple", "apply"]


def test_case_insensitive_no_match():
    result = filter_by_prefix(["banana", "cherry"], "app", case_sensitive=False)
    assert result == []
