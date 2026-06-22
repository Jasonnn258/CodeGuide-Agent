from __future__ import annotations


_COMMANDS: dict[str, str] = {}


def register(name: str, handler: str) -> None:
    _COMMANDS[name] = handler


def dispatch(name: str) -> str | None:
    return _COMMANDS.get(name)
