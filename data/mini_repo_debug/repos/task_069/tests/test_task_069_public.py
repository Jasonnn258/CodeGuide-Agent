from task_069_lib.config import get_list


def test_retrieves_existing_list():
    assert get_list('{"items": [1, 2, 3]}', "items") == [1, 2, 3]


def test_retrieves_empty_list():
    assert get_list('{"items": []}', "items") == []
