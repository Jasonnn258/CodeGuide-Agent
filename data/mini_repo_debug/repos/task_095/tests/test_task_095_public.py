from task_095_lib.commands import register, dispatch


def test_exact_match():
    register("help", "help_handler")
    assert dispatch("help") == "help_handler"


def test_missing_command():
    assert dispatch("unknown") is None


def test_multiple_commands():
    register("start", "start_handler")
    register("stop", "stop_handler")
    assert dispatch("start") == "start_handler"
    assert dispatch("stop") == "stop_handler"
