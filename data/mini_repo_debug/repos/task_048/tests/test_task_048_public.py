from datetime import date

from task_048_lib.dates import is_due


def test_past_date_is_due():
    assert is_due(date(2026, 1, 1), date(2026, 1, 2)) is True


def test_future_date_is_not_due():
    assert is_due(date(2026, 1, 3), date(2026, 1, 2)) is False
