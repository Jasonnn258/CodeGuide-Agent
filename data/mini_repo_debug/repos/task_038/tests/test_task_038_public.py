from task_038_lib.tags import ensure_tag


def test_adds_missing_tag():
    assert ensure_tag(["red"], "sale") == ["red", "sale"]


def test_does_not_mutate_input_when_adding():
    tags = ["red"]
    ensure_tag(tags, "sale")
    assert tags == ["red"]
