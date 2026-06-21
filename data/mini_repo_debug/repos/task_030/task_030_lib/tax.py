from __future__ import annotations


def tax_amount(subtotal: int, rate_percent: int) -> int:
    return subtotal * rate_percent // 100
