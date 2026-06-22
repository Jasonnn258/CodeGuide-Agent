#!/usr/bin/env python3
from __future__ import annotations

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


ROOT = Path("data/mini_repo_debug")
TASK_IDS = tuple(f"task_{index:03d}" for index in range(51, 61))
POLICIES = ("noop", "heuristic", "scripted")
ROLLOUT_DIR = ROOT / "rollouts" / "p55_051_060"
TRAJECTORIES_DIR = ROOT / "trajectories"
TEMP_ROOT = Path(DEFAULT_TEMP_ROOT) / "p55_051_060"
TIMEOUT_SECONDS = 120
PHASE_BASELINE_COUNTS = {
    "sft_total": 50,
    "preference_total": 69,
    "preference_bank_total": 69,
    "hard_preference_total": 17,
}


def main() -> int:
    before = read_counts(ROOT)
    ROLLOUT_DIR.mkdir(parents=True, exist_ok=True)
    TRAJECTORIES_DIR.mkdir(parents=True, exist_ok=True)

    rollout_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    collector = RolloutCollector(TRAJECTORIES_DIR, timeout=30)
    task_paths = {task.name: task for task in discover_tasks(ROOT) if task.name in TASK_IDS}

    for policy_name in POLICIES:
        policy_results: list[dict[str, Any]] = []
        for task_id in TASK_IDS:
            task = task_paths.get(task_id)
            if task is None:
                failures.append({"task_id": task_id, "policy": policy_name, "error": "missing_task"})
                continue
            try:
                result = collector.collect(
                    task=task,
                    policy=make_policy(policy_name),
                    temp_root=TEMP_ROOT / policy_name,
                    max_steps=8,
                    run_hidden=True,
                    keep_temp=False,
                )
                policy_results.append(_compact_rollout_result(result))
            except Exception as exc:
                failures.append({"task_id": task_id, "policy": policy_name, "error": repr(exc)})
        rollout_results.extend(policy_results)
        _write_jsonl(ROLLOUT_DIR / f"{policy_name}.jsonl", policy_results)

    command_results = [
        run_command([sys.executable, "-m", "codeguide_agent.dataset.export_training_candidates", "--root", str(ROOT), "--out", str(ROOT / "exports")]),
        run_command([sys.executable, "-m", "codeguide_agent.dataset.expand_preference_candidates", "--root", str(ROOT), "--out", str(ROOT / "preference_bank")]),
        run_command(
            [
                sys.executable,
                "-m",
                "codeguide_agent.dataset.prepare_training_package",
                "--root",
                str(ROOT),
                "--out",
                str(ROOT / "train_package"),
                "--preference-bank",
                str(ROOT / "preference_bank" / "preference_candidates.jsonl"),
            ]
        ),
        run_command(
            [
                sys.executable,
                "-m",
                "codeguide_agent.training.build_hf_training_data",
                "--package",
                str(ROOT / "train_package"),
                "--out",
                str(ROOT / "hf_training"),
            ]
        ),
    ]
    after = read_counts(ROOT)
    summary = {
        "task_ids": list(TASK_IDS),
        "policies": list(POLICIES),
        "rollout_dir": str(ROLLOUT_DIR),
        "trajectories_dir": str(TRAJECTORIES_DIR),
        "rollout_summary": summarize_rollouts(rollout_results),
        "rollout_result_count": len(rollout_results),
        "failures": failures,
        "command_results": command_results,
        "before_counts": before,
        "after_counts": after,
        "deltas": {key: after.get(key, 0) - before.get(key, 0) for key in sorted(set(before) | set(after))},
        "phase_baseline_counts": PHASE_BASELINE_COUNTS,
        "phase_deltas": {key: after.get(key, 0) - PHASE_BASELINE_COUNTS.get(key, 0) for key in sorted(PHASE_BASELINE_COUNTS)},
        "p55_succeeded": not failures
        and all(item["returncode"] == 0 for item in command_results)
        and (
            after["sft_total"] > 50
            and after["preference_total"] > 69
            and after["preference_bank_total"] > 69
            and after["hard_preference_total"] > 17
        ),
    }
    summary_path = ROLLOUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("# P55 Rollout/Export Summary")
    print(f"- tasks: {', '.join(TASK_IDS)}")
    print(f"- policies: {', '.join(POLICIES)}")
    print(f"- rollout_result_count: {len(rollout_results)}")
    print(f"- failures: {len(failures)}")
    print(f"- summary_path: {summary_path}")
    print("- counts:")
    for key in ("sft_total", "preference_total", "preference_bank_total", "hard_preference_total"):
        print(f"  - {key}: {before[key]} -> {after[key]} (delta {summary['deltas'][key]})")
    print("- phase baseline counts:")
    for key in ("sft_total", "preference_total", "preference_bank_total", "hard_preference_total"):
        print(f"  - {key}: {PHASE_BASELINE_COUNTS[key]} -> {after[key]} (delta {summary['phase_deltas'][key]})")
    print(f"- p55_succeeded: {summary['p55_succeeded']}")
    return 0 if summary["p55_succeeded"] else 1


def read_counts(root: Path) -> dict[str, int]:
    package = root / "train_package"
    bank = _read_jsonl(root / "preference_bank" / "preference_candidates.jsonl")
    hard = [
        row
        for row in bank
        if row.get("rejection_reason") == "public_pass_hidden_assertion_fail"
        or "hidden_assertion_fail" in row.get("reason_labels", [])
    ]
    return {
        "sft_total": len(_read_jsonl(package / "sft_train.jsonl")) + len(_read_jsonl(package / "sft_eval.jsonl")),
        "preference_total": len(_read_jsonl(package / "preference_train.jsonl")) + len(_read_jsonl(package / "preference_eval.jsonl")),
        "preference_bank_total": len(bank),
        "hard_preference_total": len(hard),
    }


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, capture_output=True, timeout=TIMEOUT_SECONDS, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
