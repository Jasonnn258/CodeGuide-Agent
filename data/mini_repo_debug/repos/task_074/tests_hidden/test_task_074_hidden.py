from task_074_lib.service import format_name


def test_missing_user_returns_unknown():
    db = {"u1": {"first": "Ada", "last": "Lovelace"}}
    assert format_name(db, "u2") == "Unknown"


def test_empty_db_returns_unknown():
    assert format_name({}, "anyone") == "Unknown"
