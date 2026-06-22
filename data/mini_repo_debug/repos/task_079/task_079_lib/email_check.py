from __future__ import annotations


def is_valid_email(address: str) -> bool:
    return "@" in address and "." in address
