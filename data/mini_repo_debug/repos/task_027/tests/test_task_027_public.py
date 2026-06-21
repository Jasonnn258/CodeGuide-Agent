from task_027_lib.cli import main


def test_limit_flag_reaches_renderer():
    assert main(["--limit", "3", "report"]) == "report:3"


def test_default_limit_still_works():
    assert main(["report"]) == "report:10"
