from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._timestamps: list[float] = []

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self.window
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) < self.max_calls:
            self._timestamps.append(now)
            return True
        return False

    def reset(self) -> None:
        self._timestamps = []
