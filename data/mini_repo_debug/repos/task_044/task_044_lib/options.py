from __future__ import annotations


def add_flag(flag: str, flags: list[str] = []) -> list[str]:
    flags.append(flag)
    return flags
