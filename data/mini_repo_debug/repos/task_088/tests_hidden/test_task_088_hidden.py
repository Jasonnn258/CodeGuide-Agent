from datetime import date

from task_088_lib.dates import weeks_between


def test_reversed_range_returns_positive():
    assert weeks_between(date(2026, 1, 22), date(2026, 1, 1)) == 3


def test_reversed_partial_week():
    assert weeks_between(date(2026, 1, 10), date(2026, 1, 1)) == 1
