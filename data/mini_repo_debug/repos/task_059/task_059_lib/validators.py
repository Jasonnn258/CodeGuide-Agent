from __future__ import annotations


def is_valid_username(name: str) -> bool:
    return len(name) >= 3 and name.isalnum()
