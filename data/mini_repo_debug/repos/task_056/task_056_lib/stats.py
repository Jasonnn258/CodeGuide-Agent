from __future__ import annotations

from task_056_lib.helpers import aggregate


def report(values: list[float]) -> dict:
    result = aggregate(values)
    result["mean"] = result["sum"] / result["count"]
    return result
