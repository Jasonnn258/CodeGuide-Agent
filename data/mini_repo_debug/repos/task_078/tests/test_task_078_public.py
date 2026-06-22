from task_078_lib.init_once import initialize


def test_returns_same_value_on_repeated_call():
    a = initialize("test_key", list)
    b = initialize("test_key", list)
    assert a is b


def test_different_keys_are_independent():
    a = initialize("key_a", list)
    b = initialize("key_b", list)
    assert a is not b
