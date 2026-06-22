from __future__ import annotations


def make_cache_key(func_name: str, *args: object) -> str:
    return func_name + ":" + ":".join(str(a) for a in args)
