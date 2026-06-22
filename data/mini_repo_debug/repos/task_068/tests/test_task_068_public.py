from task_068_lib.months import days_in_month


def test_january():
    assert days_in_month(2025, 1) == 31


def test_march():
    assert days_in_month(2025, 3) == 31


def test_april():
    assert days_in_month(2025, 4) == 30
