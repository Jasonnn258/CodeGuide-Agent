#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

REQUIRED = [
    "task_id",
    "bug_type",
    "difficulty",
    "public_gap",
    "hidden_gap",
    "expected_failure_mode",
    "hard_pair_potential",
]

def main() -> None:
    path = Path("data/mini_repo_debug/task_expansion_sprint_021_030.json")
    rows = json.loads(path.read_text(encoding="utf-8"))

    errors = []

    if len(rows) != 10:
        errors.append(f"expected 10 rows, got {len(rows)}")

    task_ids = [row.get("task_id") for row in rows]
    if task_ids != [f"task_{i:03d}" for i in range(21, 31)]:
        errors.append(f"unexpected task ids: {task_ids}")

    for row in rows:
        for key in REQUIRED:
            if not row.get(key):
                errors.append(f"{row.get('task_id')}: missing {key}")
        if row.get("public_gap") == row.get("hidden_gap"):
            errors.append(f"{row.get('task_id')}: public_gap equals hidden_gap")

    if errors:
        for error in errors:
            print("FAIL:", error)
        raise SystemExit(1)

    print("PASS: expansion backlog task_021-task_030 is well-formed")

if __name__ == "__main__":
    main()
