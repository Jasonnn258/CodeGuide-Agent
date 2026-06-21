from __future__ import annotations

from pricing_helpers import add_tax, subtotal


def make_invoice(items: list[dict], tax: int = 0) -> dict:
    amount = subtotal(items)
    return {"total": amount}
