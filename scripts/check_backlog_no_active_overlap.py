#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path("data/mini_repo_debug/repos")
BACKLOG_PATH = Path("data/mini_repo_debug/task_backlog.json")


def iter_task_ids(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from iter_task_ids(item)
    elif isinstance(obj, dict):
        task_id = obj.get("task_id") or obj.get("id") or obj.get("name")
        if isinstance(task_id, str) and task_id.startswith("task_"):
            yield task_id
        for value in obj.values():
            if isinstance(value, (list, dict)):
                yield from iter_task_ids(value)
    elif isinstance(obj, str) and obj.startswith("task_"):
        yield obj


def main() -> None:
    active = {p.name for p in REPO_ROOT.glob("task_*") if p.is_dir()}
    backlog = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))
    planned = set(iter_task_ids(backlog))

    overlap = sorted(active & planned)
    if overlap:
        print("FAIL: active tasks still appear in backlog:")
        for task_id in overlap:
            print(f"  - {task_id}")
        raise SystemExit(1)

    print(f"PASS: no active/planned backlog overlap ({len(active)} active, {len(planned)} planned)")


if __name__ == "__main__":
    main()
