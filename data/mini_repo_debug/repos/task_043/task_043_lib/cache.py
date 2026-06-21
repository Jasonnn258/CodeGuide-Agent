from __future__ import annotations

import json


def make_cache_key(name: str, args: tuple = (), kwargs: dict | None = None) -> str:
    return json.dumps({"name": name, "args": args}, sort_keys=True)
