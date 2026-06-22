from task_070_lib.transform import main


def test_lower_mode_is_honoured():
    assert main(["Hello", "--mode", "lower"]) == "hello"
