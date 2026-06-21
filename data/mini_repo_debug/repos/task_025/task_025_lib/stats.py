from __future__ import annotations


def moving_average(values: list[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < window:
        return []
    return [
        sum(values[i : i + window]) / window
        for i in range(0, len(values) - window)
    ]
