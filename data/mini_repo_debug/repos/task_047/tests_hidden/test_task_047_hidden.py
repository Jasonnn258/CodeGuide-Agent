from task_047_lib.profiles import with_status


def test_existing_status_is_replaced_on_copy():
    profile = {"name": "Ada", "status": "pending"}
    result = with_status(profile, "active")
    assert result == {"name": "Ada", "status": "active"}
    assert profile == {"name": "Ada", "status": "pending"}
