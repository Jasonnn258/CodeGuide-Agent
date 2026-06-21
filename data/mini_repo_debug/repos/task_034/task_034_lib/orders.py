from __future__ import annotations

from .discounts import apply_discount


def order_total(items: list[dict], discount_percent: int = 0) -> int:
    subtotal = sum(item["price"] * item.get("quantity", 1) for item in items)
    return subtotal
