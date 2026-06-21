from __future__ import annotations

from datetime import date


def is_expired(due_date: str, today: str) -> bool:
    due = date.fromisoformat(due_date)
    current = date.fromisoformat(today)
    return due < current
