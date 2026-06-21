from task_047_lib.profiles import with_status


def test_returns_updated_profile():
    assert with_status({"name": "Ada"}, "active") == {"name": "Ada", "status": "active"}


def test_original_profile_is_unchanged():
    profile = {"name": "Ada"}
    with_status(profile, "active")
    assert profile == {"name": "Ada"}
