from __future__ import annotations


def add_batch_item(item: str, batch: list[str] = []) -> list[str]:
    batch.append(item)
    return batch
