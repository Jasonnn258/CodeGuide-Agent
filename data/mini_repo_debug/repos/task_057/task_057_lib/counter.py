from __future__ import annotations


class HitCounter:
    def __init__(self, limit: int = 100) -> None:
        self.count = 0
        self.limit = limit
        self.overflow = False

    def hit(self) -> None:
        self.count += 1
        if self.count > self.limit:
            self.overflow = True

    def reset(self) -> None:
        self.count = 0
