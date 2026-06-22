from task_093_lib.matchers import filter_by_prefix


def test_case_sensitive_match():
    result = filter_by_prefix(["apple", "Apply", "banana"], "app")
    assert result == ["apple"]


def test_empty_list():
    assert filter_by_prefix([], "x") == []


def test_no_matches():
    assert filter_by_prefix(["abc", "def"], "xyz") == []
