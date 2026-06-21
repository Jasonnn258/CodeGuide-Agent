#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_ok(cmd: list[str]) -> bool:
    try:
        subprocess.check_call(cmd)
        return True
    except Exception:
        return False


def main() -> None:
    root = Path("data/mini_repo_debug")

    task_dirs = sorted((root / "tasks").glob("task_*")) if (root / "tasks").exists() else []
    repo_dirs = sorted((root / "repos").glob("task_*")) if (root / "repos").exists() else []
    active_task_count = max(len(task_dirs), len(repo_dirs))

    backlog_path = root / "task_backlog.json"
    planned_count = len(json.loads(backlog_path.read_text(encoding="utf-8"))) if backlog_path.exists() else 0

    package = root / "train_package"
    sft_total = len(read_jsonl(package / "sft_train.jsonl")) + len(read_jsonl(package / "sft_eval.jsonl"))
    pref_total = len(read_jsonl(package / "preference_train.jsonl")) + len(read_jsonl(package / "preference_eval.jsonl"))

    bank = read_jsonl(root / "preference_bank" / "preference_candidates.jsonl")
    hard_pref = [
        r for r in bank
        if r.get("rejection_reason") == "public_pass_hidden_assertion_fail"
        or "hidden_assertion_fail" in r.get("reason_labels", [])
    ]

    checks = {
        "active_task_count_ge_100": active_task_count >= 100,
        "planned_total_ge_100": active_task_count + planned_count >= 100,
        "sft_total_ge_150": sft_total >= 150,
        "preference_total_ge_100": max(pref_total, len(bank)) >= 100,
        "hard_preference_total_ge_30": len(hard_pref) >= 30,
        "clean_check_passed": run_ok(["make", "clean-check"]),
        "audit_passed": run_ok(["make", "audit"]),
    }

    ready_for_real_training = (
        checks["active_task_count_ge_100"]
        and checks["sft_total_ge_150"]
        and checks["preference_total_ge_100"]
        and checks["hard_preference_total_ge_30"]
        and checks["clean_check_passed"]
        and checks["audit_passed"]
    )

    report = {
        "active_task_count": active_task_count,
        "planned_backlog_count": planned_count,
        "planned_total_tasks": active_task_count + planned_count,
        "sft_total": sft_total,
        "preference_total": pref_total,
        "preference_bank_total": len(bank),
        "hard_preference_total": len(hard_pref),
        "checks": checks,
        "ready_for_real_training": ready_for_real_training,
        "decision": "READY" if ready_for_real_training else "NOT_READY",
        "note": "Do not claim real training readiness until active tasks and hard preference data meet thresholds.",
    }

    out = Path("docs/TRAINING_READINESS_REPORT.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("# Training Readiness Gate")
    for k, v in report.items():
        if k != "checks":
            print(f"- {k}: {v}")
    print("- checks:")
    for k, v in checks.items():
        print(f"  - {k}: {v}")

    if not ready_for_real_training:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
