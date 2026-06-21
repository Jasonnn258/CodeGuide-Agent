#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    root = Path("data/mini_repo_debug")

    tasks = sorted((root / "tasks").glob("task_*") if (root / "tasks").exists() else [])
    repos = sorted((root / "repos").glob("task_*") if (root / "repos").exists() else [])
    backlog = json.loads((root / "task_backlog.json").read_text(encoding="utf-8")) if (root / "task_backlog.json").exists() else []

    package = root / "train_package"
    sft_total = len(read_jsonl(package / "sft_train.jsonl")) + len(read_jsonl(package / "sft_eval.jsonl"))
    pref_total = len(read_jsonl(package / "preference_train.jsonl")) + len(read_jsonl(package / "preference_eval.jsonl"))

    bank = read_jsonl(root / "preference_bank" / "preference_candidates.jsonl")
    hard_pref = [
        r for r in bank
        if r.get("rejection_reason") == "public_pass_hidden_assertion_fail"
        or "hidden_assertion_fail" in r.get("reason_labels", [])
    ]

    report = {
        "existing_task_dirs": max(len(tasks), len(repos)),
        "planned_backlog_tasks": len(backlog),
        "target_total_tasks": max(len(tasks), len(repos)) + len(backlog),
        "sft_total": sft_total,
        "preference_total": pref_total,
        "preference_bank_total": len(bank),
        "hard_preference_total": len(hard_pref),
        "training_readiness": {
            "task_count_ge_100": max(len(tasks), len(repos)) + len(backlog) >= 100,
            "sft_total_ge_150": sft_total >= 150,
            "preference_total_ge_100": max(pref_total, len(bank)) >= 100,
            "hard_preference_total_ge_30": len(hard_pref) >= 30,
        },
    }

    Path("docs").mkdir(exist_ok=True)
    Path("docs/DATASET_SCALE_REPORT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("# Dataset Scale Report")
    for key, value in report.items():
        if key != "training_readiness":
            print(f"- {key}: {value}")
    print("- training_readiness:")
    for key, value in report["training_readiness"].items():
        print(f"  - {key}: {value}")


if __name__ == "__main__":
    main()
