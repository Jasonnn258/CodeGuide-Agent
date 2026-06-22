from task_073_lib.ranking import top_by_score


def test_picks_top_by_score():
    items = [{"name": "a", "s": 10}, {"name": "b", "s": 30}, {"name": "c", "s": 20}]
    result = top_by_score(items, "s", 2)
    assert len(result) == 2
    assert result[0]["name"] == "b"
    assert result[1]["name"] == "c"


def test_all_have_key():
    items = [{"name": "x", "s": 1}, {"name": "y", "s": 5}]
    result = top_by_score(items, "s", 2)
    assert result[0]["name"] == "y"
