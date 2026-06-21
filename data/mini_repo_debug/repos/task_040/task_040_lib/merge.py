from __future__ import annotations


def merge_config(defaults: dict, override: dict) -> dict:
    result = dict(defaults)
    result.update(override)
    return result
