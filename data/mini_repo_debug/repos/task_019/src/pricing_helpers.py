from __future__ import annotations


def subtotal(items: list[dict]) -> int:
    return sum(item["price"] * item.get("qty", 1) for item in items)


def add_tax(amount: int, tax: int = 0) -> int:
    return amount + tax
