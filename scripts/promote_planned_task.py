#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--planned-root", default="data/mini_repo_debug/planned_task_skeletons")
    parser.add_argument("--active-root", default="data/mini_repo_debug/tasks")
    parser.add_argument("--no-copy", action="store_true")
    args = parser.parse_args()

    task_id = args.task_id
    planned = Path(args.planned_root) / task_id
    active = Path(args.active_root) / task_id

    if not planned.exists():
        raise SystemExit(f"planned task not found: {planned}")

    run(["python", "scripts/check_planned_task_ready.py", "--task-id", task_id])

    if args.no_copy:
        print("promotion check passed; no-copy mode enabled")
        return

    if active.exists():
        raise SystemExit(f"active task already exists: {active}")

    active.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(planned, active)

    print(f"promoted {planned} -> {active}")
    print("next: run make test, make clean-check, make audit, make scale-report")


if __name__ == "__main__":
    main()
