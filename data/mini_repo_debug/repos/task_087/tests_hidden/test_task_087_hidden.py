from task_087_lib.defaults import apply_defaults


def test_original_dict_not_mutated():
    original = {"host": "localhost"}
    apply_defaults(original, {"port": 5432})
    assert original == {"host": "localhost"}


def test_original_dict_not_mutated_when_key_exists():
    original = {"host": "localhost"}
    apply_defaults(original, {"host": "default"})
    assert original == {"host": "localhost"}
