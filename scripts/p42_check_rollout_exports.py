#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ROOT = Path("data/mini_repo_debug")
TASK_IDS = tuple(f"task_{index:03d}" for index in range(31, 41))
POLICIES = ("noop", "heuristic", "scripted")


def main() -> int:
    errors: list[str] = []
    for task_id in TASK_IDS:
        paths = [ROOT / "trajectories" / f"{task_id}_{policy}.jsonl" for policy in POLICIES]
        if not any(path.exists() for path in paths):
            errors.append(f"missing trajectory for {task_id}")

    bank_rows = read_jsonl(ROOT / "preference_bank" / "preference_candidates.jsonl")
    package_pref = read_jsonl(ROOT / "train_package" / "preference_train.jsonl") + read_jsonl(ROOT / "train_package" / "preference_eval.jsonl")
    bank_task_ids = {row.get("task_id") for row in bank_rows}
    missing_bank = [task_id for task_id in TASK_IDS if task_id not in bank_task_ids]
    if missing_bank:
        errors.append(f"preference bank missing tasks: {missing_bank}")
    if len(package_pref) != len(bank_rows):
        errors.append(f"package preference count {len(package_pref)} != bank count {len(bank_rows)}")

    summary_path = ROOT / "rollouts" / "p42_031_040" / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("after_counts", {}).get("preference_bank_total") != len(bank_rows):
            errors.append("summary preference_bank_total does not match bank rows")
    else:
        errors.append("missing P42 summary.json")

    if errors:
        print("FAIL: P42 rollout/export check")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: P42 rollout/export check")
    print(f"- trajectories checked for {len(TASK_IDS)} tasks")
    print(f"- preference_bank_total: {len(bank_rows)}")
    print(f"- preference_package_total: {len(package_pref)}")
    return 0


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
