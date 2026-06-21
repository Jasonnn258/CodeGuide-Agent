from task_033_lib.catalog import visible_titles


def test_sorts_by_priority_descending():
    items = [
        {"title": "Alpha", "category": "book", "visible": True, "priority": 1},
        {"title": "Beta", "category": "book", "visible": True, "priority": 4},
        {"title": "Aardvark", "category": "book", "visible": True, "priority": 4},
    ]
    assert visible_titles(items, "book") == ["Aardvark", "Beta", "Alpha"]
