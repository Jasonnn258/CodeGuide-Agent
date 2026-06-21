from task_038_lib.tags import ensure_tag


def test_existing_tag_is_not_duplicated():
    assert ensure_tag(["red", "sale"], "sale") == ["red", "sale"]
