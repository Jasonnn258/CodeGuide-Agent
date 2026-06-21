from datetime import date

from task_048_lib.dates import is_due


def test_due_today_is_due():
    assert is_due(date(2026, 1, 2), date(2026, 1, 2)) is True
