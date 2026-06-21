from __future__ import annotations


def role_allowed(role: str, allowed_roles: list[str]) -> bool:
    return role in allowed_roles
