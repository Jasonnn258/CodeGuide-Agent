from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
