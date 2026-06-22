from task_087_lib.defaults import apply_defaults


def test_fills_missing_keys():
    result = apply_defaults({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}


def test_keeps_existing_keys():
    result = apply_defaults({"a": 1}, {"a": 99, "b": 2})
    assert result == {"a": 1, "b": 2}


def test_empty_defaults_is_noop():
    assert apply_defaults({"x": 1}, {}) == {"x": 1}
