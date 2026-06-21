from task_024_lib.tags import add_tag


def test_omitted_tags_do_not_share_state():
    assert add_tag("new") == ["new"]
    assert add_tag("sale") == ["sale"]


def test_appends_to_existing_tags():
    assert add_tag("new", ["shoe"]) == ["shoe", "new"]
