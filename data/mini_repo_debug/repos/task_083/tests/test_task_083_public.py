from task_083_lib.hashing import hash_args


def test_same_args_same_hash():
    assert hash_args(1, 2, 3) == hash_args(1, 2, 3)


def test_different_args_different_hash():
    assert hash_args(1, 2) != hash_args(1, 2, 3)
