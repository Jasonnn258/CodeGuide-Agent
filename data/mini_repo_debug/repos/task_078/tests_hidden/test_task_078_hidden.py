from task_078_lib.init_once import initialize, reset_initialized


def test_reset_allows_reinitialization():
    a = initialize("resettable", list)
    reset_initialized("resettable")
    b = initialize("resettable", list)
    assert a is not b


def test_reset_all_clears_everything():
    a = initialize("k1", list)
    b = initialize("k2", list)
    reset_initialized()
    c = initialize("k1", list)
    assert a is not c
    assert initialize("k2", list) is not b
