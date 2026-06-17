from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.eval.run_eval import DEFAULT_TEMP_ROOT, discover_tasks, pytest_available, pytest_required, DEV_INSTALL_MESSAGE
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import make_policy


def summarize_rollouts(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    if count == 0:
        return {
            "num_tasks": 0,
            "success_rate": 0.0,
            "average_steps": 0.0,
            "invalid_action_rate": 0.0,
            "original_repo_unchanged_rate": 0.0,
        }
    return {
        "num_tasks": count,
        "success_rate": round(sum(1 for item in results if item.get("success")) / count, 4),
        "average_steps": round(sum(float(item.get("steps", 0)) for item in results) / count, 4),
        "invalid_action_rate": round(sum(1 for item in results if item.get("invalid_action_count", 0) > 0) / count, 4),
        "original_repo_unchanged_rate": round(sum(1 for item in results if item.get("original_repo_unchanged")) / count, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect deterministic Mini-Repo-Debug rollouts.")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--task-id")
    parser.add_argument("--policy", choices=["noop", "scripted", "gold"], default="noop")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--temp-root", default=str(DEFAULT_TEMP_ROOT))
    parser.add_argument("--run-hidden", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--output", default="data/mini_repo_debug/rollouts/phase2_rollouts.jsonl")
    parser.add_argument("--trajectories-dir", default="data/mini_repo_debug/trajectories")
    args = parser.parse_args()

    tasks = discover_tasks(args.root, task_id=args.task_id)
    if not tasks:
        print(f"No tasks found for root={args.root!r} task_id={args.task_id!r}")
        return 1
    if pytest_required(tasks, args.run_hidden) and not pytest_available():
        print(DEV_INSTALL_MESSAGE)
        return 2

    collector = RolloutCollector(args.trajectories_dir, keep_temp=args.keep_temp)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with output_path.open("w", encoding="utf-8") as handle:
        for task in tasks:
            result = collector.collect(
                task=task,
                policy=make_policy(args.policy),
                temp_root=args.temp_root,
                max_steps=args.max_steps,
                run_hidden=args.run_hidden,
                keep_temp=args.keep_temp,
            )
            results.append(result)
            handle.write(json.dumps(result, sort_keys=True) + "\n")

    summary = summarize_rollouts(results)
    print("Rollout Summary")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0 if all(item.get("original_repo_unchanged") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
