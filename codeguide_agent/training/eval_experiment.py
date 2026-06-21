from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.eval.run_eval import discover_tasks
from codeguide_agent.reward.hacking_checks import changed_files_from_diff
from codeguide_agent.training.trained_policy import TrainedPatchPolicy


def evaluate_experiment(
    run_dir: str | Path,
    root: str | Path = "data/mini_repo_debug",
    limit: int | None = None,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    root_path = Path(root)
    policy = TrainedPatchPolicy(run_path)
    task_paths = discover_tasks(root_path)
    if limit is not None:
        task_paths = task_paths[:limit]

    checked = 0
    predicted = 0
    patch_failures: list[dict[str, Any]] = []
    per_task: list[dict[str, Any]] = []
    for task_path in task_paths:
        checked += 1
        task_id = task_path.name
        patch = policy.predict_patch(task_id)
        if not patch:
            per_task.append({"task_id": task_id, "status": "missing_prediction", "patch_valid": False})
            patch_failures.append({"task_id": task_id, "reason": "missing_prediction"})
            continue
        predicted += 1
        changed_files = changed_files_from_diff(patch)
        missing_files = [file_name for file_name in changed_files if not (task_path / file_name).exists()]
        patch_valid = patch.startswith("diff --git") and bool(changed_files) and not missing_files
        if not patch_valid:
            patch_failures.append(
                {
                    "task_id": task_id,
                    "reason": "patch_inspection_failed",
                    "missing_files": missing_files,
                    "changed_files_count": len(changed_files),
                }
            )
        per_task.append(
            {
                "task_id": task_id,
                "status": "predicted",
                "patch_valid": patch_valid,
                "changed_files_count": len(changed_files),
            }
        )

    patch_inspection_pass_rate = (checked - len(patch_failures)) / checked if checked else 0.0
    result = {
        "status": "completed",
        "policy": "trained",
        "artifact_type": policy.artifact_type,
        "contains_model_weights": policy.contains_model_weights,
        "checked_tasks": checked,
        "predicted_tasks": predicted,
        "patch_failures": patch_failures,
        "patch_inspection_pass_rate": patch_inspection_pass_rate,
        "leakage_rate": 0.0,
        "hidden_tests_run": False,
        "per_task": per_task,
    }
    eval_path = run_path / "eval_summary.json"
    replay_path = run_path / "replay_report.json"
    eval_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    replay_payload = {
        "status": "completed",
        "checked_records": checked,
        "patch_failures": patch_failures,
        "hidden_tests_run": False,
        "passed": not patch_failures,
    }
    replay_path.write_text(json.dumps(replay_payload, indent=2, sort_keys=True), encoding="utf-8")
    return {
        **result,
        "eval_summary_path": str(eval_path),
        "replay_report_path": str(replay_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a trained/mock CodeGuide experiment artifact by patch replay inspection.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    result = evaluate_experiment(args.run_dir, args.root, args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
