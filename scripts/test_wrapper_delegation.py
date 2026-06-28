#!/usr/bin/env python3
"""Smoke: verify each legacy wrapper delegates correct args to the unified runner.

Does NOT launch rollouts — monkeypatches run_bounded_rollout_export.main to
capture parsed arguments and returns 0 immediately.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

WRAPPERS = [
    ("scripts/p34_rollout_export_021_025.py", dict(task_start=21, task_end=25, phase="p34")),
    ("scripts/p38_rollout_export_026_030.py", dict(task_start=26, task_end=30, phase="p38")),
    ("scripts/p42_rollout_export_031_040.py", dict(task_start=31, task_end=40, phase="p42")),
    ("scripts/p50_rollout_export_041_050.py", dict(task_start=41, task_end=50, phase="p50")),
    ("scripts/p55_rollout_export_051_060.py", dict(task_start=51, task_end=60, phase="p55")),
    ("scripts/p61_rollout_export_061_100.py", dict(task_start=61, task_end=100, phase="p61")),
]


def _fake_main() -> int:
    """Capture args from the real argparse parser, then return 0 without side effects."""
    import scripts.run_bounded_rollout_export as _runner_mod

    parser = _runner_mod._build_parser()
    args = parser.parse_args()
    _captured_args.append(
        dict(task_start=args.task_start, task_end=args.task_end, phase=args.phase)
    )
    return 0


_captured_args: list[dict[str, Any]] = []


def main() -> int:
    # Monkeypatch before any wrapper import
    import scripts.run_bounded_rollout_export as _runner_mod

    _runner_mod.main = _fake_main

    failures: list[str] = []
    for rel_path, expected in WRAPPERS:
        _captured_args.clear()
        wrapper_path = REPO_ROOT / rel_path
        try:
            runpy.run_path(str(wrapper_path), run_name="__main__")
        except SystemExit:
            pass
        if not _captured_args:
            failures.append(f"{rel_path}: main() was never called")
            continue
        captured = _captured_args[0]
        if captured != expected:
            failures.append(
                f"{rel_path}: expected {expected}, got {captured}"
            )

    if failures:
        print("FAIL: wrapper delegation mismatch")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"OK: {len(WRAPPERS)} wrappers delegate correct args to unified runner")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
