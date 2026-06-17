from __future__ import annotations

from calculator import final_total
from formatter import format_total


def order_summary(order: dict) -> str:
    amount = final_total(order["items"], discount=order.get("discount", 0))
    return format_total(amount)
