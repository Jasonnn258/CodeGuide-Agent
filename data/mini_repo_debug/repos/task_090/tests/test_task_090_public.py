from task_090_lib.repeat import main


def test_single_repetition():
    assert main(["hello"]) == "hello"


def test_count_one_explicit():
    assert main(["hello", "--count", "1"]) == "hello"


def test_custom_separator():
    assert main(["a", "--sep", ","]) == "a"
