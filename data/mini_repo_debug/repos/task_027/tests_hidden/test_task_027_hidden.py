from task_027_lib.cli import main


def test_uppercase_flag_reaches_renderer():
    assert main(["--uppercase", "report"]) == "REPORT:10"


def test_flags_can_be_combined():
    assert main(["--uppercase", "--limit", "2", "report"]) == "REPORT:2"
