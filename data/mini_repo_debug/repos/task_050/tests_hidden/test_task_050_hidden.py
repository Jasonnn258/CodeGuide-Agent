from task_050_lib.cli import main


def test_multi_word_prefix_is_used():
    assert main(["Ada", "--prefix", "Good morning"]) == "Good morning, Ada!"
