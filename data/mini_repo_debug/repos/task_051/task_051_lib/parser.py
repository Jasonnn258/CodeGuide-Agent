from __future__ import annotations


def parse_int(value) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
