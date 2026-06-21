from task_044_lib.options import add_flag


def test_input_flags_are_not_mutated():
    existing = ["--json"]
    result = add_flag("--verbose", existing)
    assert result == ["--json", "--verbose"]
    assert existing == ["--json"]
