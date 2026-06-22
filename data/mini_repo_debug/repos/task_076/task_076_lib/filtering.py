from __future__ import annotations

from task_076_lib.validator import is_even


def filter_valid(numbers: list[int]) -> list[int]:
    return [n for n in numbers if is_even(n)]
