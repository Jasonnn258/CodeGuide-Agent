from __future__ import annotations


def clamp_index(index: int, size: int) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    if index < 0:
        return 0
    if index > size:
        return size - 1
    return index
