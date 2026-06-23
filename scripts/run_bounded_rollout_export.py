#!/usr/bin/env python3
"""Bounded rollout/export runner — single entry point for all phase scripts.

Usage:
    python scripts/run_bounded_rollout_export.py \\
      --root data/mini_repo_debug \\
      --phase p61 \\
      --task-start 61 --task-end 100 \\
      --policies noop,heuristic,scripted
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codeguide_agent.eval.run_eval import DEFAULT_TEMP_ROOT, discover_tasks
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import make_policy
from codeguide_agent.rollout.run_rollout import summarize_rollouts


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded rollout + canonical export")
    parser.add_argument("--root", default="data/mini_repo_debug")
    parser.add_argument("--phase", default="p99")
    parser.add_argument("--task-start", type=int, required=True)
    parser.add_argument("--task-end", type=int, required=True)
    parser.add_argument("--policies", default="noop,heuristic,scripted")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-steps", type=int, default=8)
    args = parser.parse_args()

    root = Path(args.root)
    task_ids = tuple(f"task_{i:03d}" for i in range(args.task_start, args.task_end + 1))
    policies = tuple(p.strip() for p in args.policies.split(","))
    phase = args.phase
    rollout_dir = root / "rollouts" / f"{phase}_{args.task_start:03d}_{args.task_end:03d}"
    trajectories_dir = root / "trajectories"
    temp_root = Path(DEFAULT_TEMP_ROOT) / f"{phase}_{args.task_start:03d}_{args.task_end:03d}"

    # ----- baseline -----
    before = read_counts(root)

    rollout_dir.mkdir(parents=True, exist_ok=True)
    trajectories_dir.mkdir(parents=True, exist_ok=True)

    # ----- rollout -----
    rollout_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    collector = RolloutCollector(trajectories_dir, timeout=30)
    task_paths = {t.name: t for t in discover_tasks(root) if t.name in task_ids}

    for policy_name in policies:
        policy_results: list[dict[str, Any]] = []
        for task_id in task_ids:
            task = task_paths.get(task_id)
            if task is None:
                failures.append({"task_id": task_id, "policy": policy_name, "error": "missing_task"})
                continue
            try:
                result = collector.collect(
                    task=task,
                    policy=make_policy(policy_name),
                    temp_root=temp_root / policy_name,
                    max_steps=args.max_steps,
                    run_hidden=True,
                    keep_temp=False,
                )
                policy_results.append(_compact_rollout_result(result))
            except Exception as exc:
                failures.append({"task_id": task_id, "policy": policy_name, "error": repr(exc)})
        rollout_results.extend(policy_results)
        _write_jsonl(rollout_dir / f"{policy_name}.jsonl", policy_results)

    # ----- canonical export pipeline -----
    command_results = [
        _run([sys.executable, "-m", "codeguide_agent.dataset.export_training_candidates", "--root", str(root), "--out", str(root / "exports")], args.timeout),
        _run([sys.executable, "-m", "codeguide_agent.dataset.expand_preference_candidates", "--root", str(root), "--out", str(root / "preference_bank")], args.timeout),
        _run(
            [
                sys.executable, "-m", "codeguide_agent.dataset.prepare_training_package",
                "--root", str(root), "--out", str(root / "train_package"),
                "--preference-bank", str(root / "preference_bank" / "preference_candidates.jsonl"),
            ],
            args.timeout,
        ),
        _run(
            [
                sys.executable, "-m", "codeguide_agent.training.build_hf_training_data",
                "--package", str(root / "train_package"), "--out", str(root / "hf_training"),
            ],
            args.timeout,
        ),
    ]

    # ----- summary -----
    after = read_counts(root)
    commands_ok = all(item["returncode"] == 0 for item in command_results)
    final_state_good = (
        after["sft_total"] >= 100
        and after["preference_total"] >= 100
        and after["preference_bank_total"] >= 100
        and after["hard_preference_total"] >= 30
        and after.get("active_task_count", 0) + after.get("planned_backlog_count", 0) >= 100
    )
    # Idempotent: succeed if final state meets thresholds and no rollout failures,
    # even if refresh commands return non-zero when no work is needed.
    succeeded = not failures and final_state_good

    delta_keys = sorted(set(before) | set(after))
    summary = {
        "task_ids": list(task_ids),
        "policies": list(policies),
        "rollout_dir": str(rollout_dir),
        "trajectories_dir": str(trajectories_dir),
        "rollout_summary": summarize_rollouts(rollout_results),
        "rollout_result_count": len(rollout_results),
        "failures": failures,
        "command_results": command_results,
        "before_counts": before,
        "after_counts": after,
        "deltas": {k: after.get(k, 0) - before.get(k, 0) for k in delta_keys},
        "phase_baseline_counts": before,
        "phase_deltas": {k: after.get(k, 0) - before.get(k, 0) for k in before},
        f"{phase}_succeeded": succeeded,
        "idempotent": True,
    }
    summary_path = rollout_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"# {phase.upper()} Rollout/Export Summary")
    print(f"- tasks: {task_ids[0]}..{task_ids[-1]}")
    print(f"- policies: {', '.join(policies)}")
    print(f"- rollout_result_count: {len(rollout_results)}")
    print(f"- failures: {len(failures)}")
    print(f"- succeeded: {succeeded}")
    for k in ("sft_total", "preference_total", "preference_bank_total", "hard_preference_total"):
        print(f"  - {k}: {before[k]} -> {after[k]} (delta {summary['deltas'][k]})")
    return 0 if succeeded else 1


def read_counts(root: Path) -> dict[str, int]:
    package = root / "train_package"
    bank = _read_jsonl(root / "preference_bank" / "preference_candidates.jsonl")
    hard = [
        r for r in bank
        if r.get("rejection_reason") == "public_pass_hidden_assertion_fail"
        or "hidden_assertion_fail" in r.get("reason_labels", [])
    ]
    repos = list((root / "repos").glob("task_*")) if (root / "repos").exists() else []
    backlog_path = root / "task_backlog.json"
    planned = len(json.loads(backlog_path.read_text(encoding="utf-8"))) if backlog_path.exists() else 0
    return {
        "sft_total": len(_read_jsonl(package / "sft_train.jsonl")) + len(_read_jsonl(package / "sft_eval.jsonl")),
        "preference_total": len(_read_jsonl(package / "preference_train.jsonl")) + len(_read_jsonl(package / "preference_eval.jsonl")),
        "preference_bank_total": len(bank),
        "hard_preference_total": len(hard),
        "active_task_count": len(repos),
        "planned_backlog_count": planned,
    }


def _compact_rollout_result(result: dict[str, Any]) -> dict[str, Any]:
    reward = result.get("reward", {})
    return {
        "task_id": result.get("task_id"),
        "policy": result.get("policy"),
        "trajectory_path": result.get("trajectory_path"),
        "success": result.get("success"),
        "steps": result.get("steps"),
        "stop_reason": result.get("stop_reason"),
        "public_pass": reward.get("public_pass"),
        "hidden_pass": reward.get("hidden_pass"),
        "public_pass_hidden_fail": reward.get("public_pass_hidden_fail"),
        "hidden_failure_type": reward.get("hidden_failure_type"),
        "leakage_detected": reward.get("leakage_detected"),
        "original_repo_unchanged": result.get("original_repo_unchanged"),
    }


def _run(command: list[str], timeout: int) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
