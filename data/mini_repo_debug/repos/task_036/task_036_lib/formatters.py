from __future__ import annotations


def format_currency(cents: int) -> str:
    return f"${cents / 100:.2f}"
