from task_095_lib.commands import register, dispatch


def test_uppercase_dispatch():
    register("help", "help_handler")
    assert dispatch("HELP") == "help_handler"


def test_mixed_case_register_and_dispatch():
    register("MyCmd", "my_handler")
    assert dispatch("mycmd") == "my_handler"
    assert dispatch("MYCMD") == "my_handler"
