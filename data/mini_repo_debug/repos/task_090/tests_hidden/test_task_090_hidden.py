from task_090_lib.repeat import main


def test_repeat_three_times():
    assert main(["x", "--count", "3"]) == "x x x"


def test_repeat_with_custom_sep_and_count():
    assert main(["y", "--count", "2", "--sep", "-"]) == "y-y"
