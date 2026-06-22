from task_068_lib.months import days_in_month


def test_february_leap_year():
    assert days_in_month(2024, 2) == 29


def test_february_non_leap_year():
    assert days_in_month(2025, 2) == 28


def test_february_century_non_leap():
    assert days_in_month(1900, 2) == 28


def test_february_century_leap():
    assert days_in_month(2000, 2) == 29
