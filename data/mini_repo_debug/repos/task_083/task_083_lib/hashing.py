from __future__ import annotations

import hashlib


def hash_args(*args: object) -> str:
    raw = ":".join(str(a) for a in args)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
