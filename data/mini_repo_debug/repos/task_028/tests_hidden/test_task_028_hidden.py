from task_028_lib.ranking import active_names


def test_sorts_by_score_descending():
    users = [
        {"name": "Ada", "active": True, "score": 5},
        {"name": "Cal", "active": True, "score": 9},
        {"name": "Bea", "active": True, "score": 7},
    ]
    assert active_names(users) == ["Cal", "Bea", "Ada"]


def test_ties_sort_by_name():
    users = [
        {"name": "Zo", "active": True, "score": 5},
        {"name": "Al", "active": True, "score": 5},
    ]
    assert active_names(users) == ["Al", "Zo"]
