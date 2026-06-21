from task_032_lib.percent import percent_change


def test_percent_increase():
    assert percent_change(100, 125) == 25


def test_percent_decrease():
    assert percent_change(200, 150) == -25
