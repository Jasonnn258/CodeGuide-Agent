from __future__ import annotations


def apply_discount(amount: int, percent: int) -> int:
    return amount - (amount * percent // 100)
