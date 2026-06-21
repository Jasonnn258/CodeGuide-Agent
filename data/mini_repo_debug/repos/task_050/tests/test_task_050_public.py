from task_050_lib.cli import main


def test_custom_prefix_is_used():
    assert main(["Ada", "--prefix", "Hi"]) == "Hi, Ada!"


def test_default_prefix_still_works():
    assert main(["Ada"]) == "Hello, Ada!"
