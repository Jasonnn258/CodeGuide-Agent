from __future__ import annotations


def layered_merge(*layers: dict) -> dict:
    result: dict = {}
    for layer in layers:
        for key, value in layer.items():
            if isinstance(value, list) and key in result and isinstance(result[key], list):
                result[key] = result[key] + value
            else:
                result[key] = value
    return result
