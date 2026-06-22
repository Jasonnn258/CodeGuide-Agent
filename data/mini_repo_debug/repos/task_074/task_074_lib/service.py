from __future__ import annotations


def fetch_user(users_db: dict[str, dict], user_id: str) -> dict | None:
    return users_db.get(user_id)


def format_name(users_db: dict[str, dict], user_id: str) -> str:
    user = fetch_user(users_db, user_id)
    return f"{user['first']} {user['last']}"
