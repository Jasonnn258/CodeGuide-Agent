from __future__ import annotations


def aggregate(values: list[float]) -> dict:
    return {"sum": sum(values), "count": len(values)}
