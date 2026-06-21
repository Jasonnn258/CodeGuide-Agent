from task_028_lib.ranking import active_names


def test_filters_inactive_users():
    users = [
        {"name": "Ada", "active": True, "score": 5},
        {"name": "Ben", "active": False, "score": 100},
        {"name": "Cal", "active": True, "score": 3},
    ]
    assert active_names(users) == ["Ada", "Cal"]


def test_applies_min_score():
    users = [
        {"name": "Ada", "active": True, "score": 5},
        {"name": "Cal", "active": True, "score": 3},
    ]
    assert active_names(users, min_score=4) == ["Ada"]
