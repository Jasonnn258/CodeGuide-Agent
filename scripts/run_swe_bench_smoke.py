#!/usr/bin/env python3
"""SWE-bench Lite smoke eval using Mini-Repo-Debug tasks.

Converts 5 Mini-Repo-Debug tasks to SWE-bench format, applies gold patches
as "agent patches", and verifies the eval adapter correctly reports
resolved/unresolved.

Usage:
    python scripts/run_swe_bench_smoke.py \\
      --root data/mini_repo_debug \\
      --out data/mini_repo_debug/swe_bench_smoke.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.eval.swe_bench_adapter import (
    convert_mini_repo_task,
    evaluate_batch,
    evaluate_swe_task,
    load_swe_bench_tasks,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="SWE-bench Lite smoke eval")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="data/mini_repo_debug/swe_bench_smoke.json")
    parser.add_argument("--num-tasks", type=int, default=5, help="Number of tasks to smoke-test")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for task selection")
    args = parser.parse_args()

    root = Path(args.root)
    repos_dir = root / "repos"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    task_dirs = sorted(repos_dir.glob("task_*"))
    rng = random.Random(args.seed)
    selected = rng.sample(task_dirs, min(args.num_tasks, len(task_dirs)))

    results = run_smoke(selected, root)

    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("# SWE-bench Lite Smoke Eval")
    print(f"  tasks: {results['total']}")
    print(f"  resolved: {results['resolved']}")
    print(f"  unresolved: {results['unresolved']}")
    print(f"  errors: {results['error_count']}")
    print(f"  resolve_rate: {results['resolve_rate']:.4f}")
    print(f"  passed: {results['passed']}")

    return 0 if results["passed"] else 1


def run_smoke(task_dirs: list[Path], root: Path) -> dict[str, Any]:
    # Convert to SWE-bench format
    tasks = []
    gold_metadata: dict[str, dict[str, Any]] = {}

    # Load gold file/function references from training data
    train_pkg = root / "train_package"
    sft_path = train_pkg / "sft_train.jsonl"
    if sft_path.exists():
        for line in sft_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            tid = d.get("task_id", "")
            loc = d.get("localization", {})
            if tid and loc:
                gold_metadata[tid] = {
                    "gold_files": loc.get("gold_files", []),
                    "gold_functions": loc.get("gold_functions", []),
                }

    for td in task_dirs:
        meta = gold_metadata.get(td.name, {})
        task = convert_mini_repo_task(td, **meta)
        tasks.append(task)

    # Build patches: use gold patches as "agent patches" (should resolve)
    patches: dict[str, str] = {}
    for task in tasks:
        patches[task.instance_id] = task.gold_patch

    # Evaluate
    batch_result = evaluate_batch(tasks, patches, timeout=120)

    # Smoke checks
    per_task = []
    for task in tasks:
        r = evaluate_swe_task(task, patches.get(task.instance_id, ""), timeout=120)
        per_task.append({
            "instance_id": task.instance_id,
            "resolved": r.resolved,
            "repo_setup_ok": r.repo_setup_ok,
            "patch_applied_ok": r.patch_applied_ok,
            "error": r.error,
        })

    # Verify: gold patches should resolve their own tasks
    resolved_count = sum(1 for t in per_task if t["resolved"])
    all_gold_resolved = resolved_count == len(tasks)

    # Also test empty patch (should NOT resolve)
    empty_results = []
    for task in tasks:
        r = evaluate_swe_task(task, "", timeout=120)
        empty_results.append({
            "instance_id": task.instance_id,
            "resolved": r.resolved,
            "error": r.error,
        })
    all_empty_unresolved = all(not r["resolved"] for r in empty_results)

    passed = all_gold_resolved and all_empty_unresolved

    return {
        "total": len(tasks),
        "resolved": batch_result["resolved"],
        "unresolved": batch_result["unresolved"],
        "error_count": batch_result["error_count"],
        "resolve_rate": batch_result["resolve_rate"],
        "all_gold_resolved": all_gold_resolved,
        "all_empty_unresolved": all_empty_unresolved,
        "passed": passed,
        "per_task_gold": per_task,
        "per_task_empty": empty_results,
        "task_ids": [t.instance_id for t in tasks],
    }


if __name__ == "__main__":
    raise SystemExit(main())
