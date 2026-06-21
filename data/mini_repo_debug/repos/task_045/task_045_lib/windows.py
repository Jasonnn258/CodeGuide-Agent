from __future__ import annotations


def take_window(values: list[int], start: int, size: int) -> list[int]:
    if start + size >= len(values):
        return []
    return values[start : start + size]
