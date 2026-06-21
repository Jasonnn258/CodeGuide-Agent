from __future__ import annotations


def active_names(users: list[dict], min_score: int = 0) -> list[str]:
    active = [user for user in users if user.get("active") and user.get("score", 0) >= min_score]
    return [user["name"] for user in sorted(active, key=lambda user: user["name"])]
