from __future__ import annotations

from datetime import date, timedelta


def weeks_between(start: date, end: date) -> int:
    return (end - start).days // 7
