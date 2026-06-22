from task_070_lib.transform import main


def test_default_mode_is_upper():
    assert main(["hello"]) == "HELLO"


def test_explicit_upper_mode():
    assert main(["hello", "--mode", "upper"]) == "HELLO"
