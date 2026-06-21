from __future__ import annotations


def merge_defaults(config: dict, defaults: dict) -> dict:
    defaults.update(config)
    return defaults
