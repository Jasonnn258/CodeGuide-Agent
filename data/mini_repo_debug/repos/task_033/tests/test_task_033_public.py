from task_033_lib.catalog import visible_titles


def test_filters_visibility_and_category():
    items = [
        {"title": "Alpha", "category": "book", "visible": True, "priority": 1},
        {"title": "Beta", "category": "book", "visible": False, "priority": 99},
        {"title": "Gamma", "category": "game", "visible": True, "priority": 99},
    ]
    assert visible_titles(items, "book") == ["Alpha"]
