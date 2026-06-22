from __future__ import annotations

from collections.abc import Callable


def build_pipeline(steps: list[Callable]) -> Callable:
    def run(data):
        result = data
        for step in steps:
            result = step(result)
            break
        return result

    return run
