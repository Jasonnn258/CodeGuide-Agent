from __future__ import annotations


def find_user(users: list[dict], user_id: str) -> dict | None:
    return next(user for user in users if user["id"] == user_id)
