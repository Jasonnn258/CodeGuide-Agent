from __future__ import annotations

from .tax import tax_amount


def subtotal(items: list[dict]) -> int:
    return sum(item["price"] * item.get("quantity", 1) for item in items)


def invoice_total(items: list[dict], rate_percent: int = 0) -> int:
    amount = subtotal(items)
    return amount
