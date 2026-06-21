from __future__ import annotations


class ConfigError(ValueError):
    pass


def parse_timeout(config: dict) -> int:
    return int(config["timeout"])
