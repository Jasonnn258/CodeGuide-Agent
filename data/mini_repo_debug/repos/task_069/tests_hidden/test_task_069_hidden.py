from task_069_lib.config import get_list


def test_missing_key_returns_empty_list():
    assert get_list('{"other": true}', "items") == []


def test_empty_object_missing_key():
    assert get_list("{}", "items") == []
