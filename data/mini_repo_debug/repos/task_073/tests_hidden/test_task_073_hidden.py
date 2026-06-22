from task_073_lib.ranking import top_by_score


def test_missing_key_treated_as_zero():
    items = [{"name": "a"}, {"name": "b", "s": 5}]
    result = top_by_score(items, "s", 2)
    assert result[0]["name"] == "b"


def test_all_missing_key_sorts_stably():
    items = [{"name": "first"}, {"name": "second"}]
    result = top_by_score(items, "s", 2)
    assert len(result) == 2
