from __future__ import annotations

from task_096_lib.models import Item


def cart_total(items: list[Item]) -> float:
    return sum(item.price for item in items)
