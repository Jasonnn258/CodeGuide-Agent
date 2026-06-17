from __future__ import annotations


class PriceService:
    def __init__(self, prices: dict[tuple[str, str], int]):
        self.prices = prices
        self.cache: dict[str, int] = {}

    def get_price(self, item: str, region: str) -> int:
        key = item
        if key not in self.cache:
            self.cache[key] = self.prices[(item, region)]
        return self.cache[key]
