from __future__ import annotations


def safe_percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return (part / whole) * 100
