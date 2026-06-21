#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


POLICIES = ["prompt_only", "llm_baseline", "strong_llm_optional"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--out", default="docs/ROLLOUT_BATCH_PLAN.json")
    parser.add_argument("--policies", default=",".join(POLICIES))
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.add_argument("--budget-note", default="offline plan only; do not run paid APIs without explicit approval")
    args = parser.parse_args()

    root = Path(args.root)
    policies = [x.strip() for x in args.policies.split(",") if x.strip()]

    task_dirs = sorted((root / "tasks").glob("task_*")) if (root / "tasks").exists() else []
    if not task_dirs:
        task_dirs = sorted((root / "repos").glob("task_*")) if (root / "repos").exists() else []

    jobs = []
    for task in task_dirs:
        for policy in policies:
            jobs.append({
                "task_id": task.name,
                "policy": policy,
                "status": "planned",
                "trajectory_path": f"data/mini_repo_debug/trajectories/{task.name}_{policy}.jsonl",
            })

    report = {
        "task_count": len(task_dirs),
        "policy_count": len(policies),
        "planned_rollout_jobs": len(jobs),
        "max_concurrency": args.max_concurrency,
        "budget_note": args.budget_note,
        "jobs": jobs,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("# Rollout Batch Plan")
    print(f"- task_count: {report['task_count']}")
    print(f"- policy_count: {report['policy_count']}")
    print(f"- planned_rollout_jobs: {report['planned_rollout_jobs']}")
    print(f"- max_concurrency: {report['max_concurrency']}")
    print(f"- out: {out}")


if __name__ == "__main__":
    main()
