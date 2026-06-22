from datetime import date

from task_088_lib.dates import weeks_between


def test_positive_range():
    assert weeks_between(date(2026, 1, 1), date(2026, 1, 22)) == 3


def test_same_date():
    assert weeks_between(date(2026, 6, 1), date(2026, 6, 1)) == 0


def test_one_week():
    assert weeks_between(date(2026, 1, 1), date(2026, 1, 8)) == 1
