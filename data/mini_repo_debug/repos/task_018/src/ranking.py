from __future__ import annotations


def top_active(users: list[dict], limit: int) -> list[str]:
    active = [user for user in users if user.get("active")]
    ranked = sorted(active, key=lambda user: user["score"])
    return [user["name"] for user in ranked[:limit]]
