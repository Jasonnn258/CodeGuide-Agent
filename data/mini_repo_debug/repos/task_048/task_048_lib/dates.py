from __future__ import annotations

from datetime import date


def is_due(due_on: date, today: date) -> bool:
    return due_on < today
