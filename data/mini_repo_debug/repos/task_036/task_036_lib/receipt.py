from __future__ import annotations

from .formatters import format_currency


def render_receipt(total_cents: int) -> str:
    return f"Total: {total_cents}"
