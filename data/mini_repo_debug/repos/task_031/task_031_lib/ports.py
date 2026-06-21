from __future__ import annotations


class ConfigError(ValueError):
    pass


def parse_port(config: dict) -> int:
    return int(config.get("port", 8080))
