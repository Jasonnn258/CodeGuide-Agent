from task_044_lib.options import add_flag


def test_default_flags_are_independent():
    assert add_flag("--debug") == ["--debug"]
    assert add_flag("--quiet") == ["--quiet"]
