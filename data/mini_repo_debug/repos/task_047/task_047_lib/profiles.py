from __future__ import annotations


def with_status(profile: dict, status: str) -> dict:
    profile["status"] = status
    return profile
