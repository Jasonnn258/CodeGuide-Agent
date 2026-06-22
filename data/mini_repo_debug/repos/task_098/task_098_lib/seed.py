from __future__ import annotations

_SEEDED: bool = False


def ensure_seeded(seed: int = 42) -> None:
    global _SEEDED
    if not _SEEDED:
        import random
        random.seed(seed)
        _SEEDED = True
