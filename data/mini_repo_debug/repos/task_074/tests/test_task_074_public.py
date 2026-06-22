from task_074_lib.service import format_name


def test_formats_existing_user():
    db = {"u1": {"first": "Ada", "last": "Lovelace"}}
    assert format_name(db, "u1") == "Ada Lovelace"


def test_formats_another_user():
    db = {"a": {"first": "Alan", "last": "Turing"}}
    assert format_name(db, "a") == "Alan Turing"
