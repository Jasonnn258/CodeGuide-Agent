from __future__ import annotations


def has_role(user_roles: list[str], required: str) -> bool:
    return required in user_roles
