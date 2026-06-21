from task_040_lib.merge import merge_config


def test_top_level_override():
    assert merge_config({"debug": False}, {"debug": True}) == {"debug": True}


def test_keeps_unmentioned_top_level_default():
    assert merge_config({"debug": False, "retries": 3}, {"debug": True})["retries"] == 3
