from __future__ import annotations


class IntStack:
    def __init__(self) -> None:
        self._items: list[int] = []
        self._popped: list[int] = []

    def push(self, value: int) -> None:
        self._items.append(value)

    def pop(self) -> int | None:
        if not self._items:
            return None
        value = self._items.pop()
        self._popped.append(value)
        return value

    def size(self) -> int:
        return len(self._items)

    def popped_count(self) -> int:
        return len(self._popped)

    def clear(self) -> None:
        self._items.clear()
