from task_083_lib.hashing import hash_args


def test_dict_order_does_not_matter():
    a = hash_args({"a": 1, "b": 2})
    b = hash_args({"b": 2, "a": 1})
    assert a == b


def test_list_with_same_elements():
    assert hash_args([1, 2, 3]) == hash_args([1, 2, 3])


def test_tuple_and_list_of_same_values_same_hash():
    assert hash_args([1, 2]) == hash_args((1, 2))
