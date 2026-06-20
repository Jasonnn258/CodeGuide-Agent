from __future__ import annotations

"""Forge baseline comparison entry point.

The canonical Phase 2 rollout/evaluation path is
`codeguide_agent.rollout.run_rollout`. This module remains useful for comparing
the migrated forge-style runtime, but it uses the canonical reward calculator
so its reward totals stay comparable.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codeguide_agent.baselines.forge_runner import run_forge_baseline
from codeguide_agent.datasets.mini_repo_debug import MiniRepoDebugTask, load_tasks
from codeguide_agent.eval.run_eval import compute_repo_checksum
from codeguide_agent.evaluators.patch_eval import evaluate_patch
from codeguide_agent.reward.calculator import calculate_reward


DEFAULT_REPORT_DIR = Path("data/mini_repo_debug/reports")
DEFAULT_TRAJECTORY_DIR = Path("data/mini_repo_debug/trajectories")
DEFAULT_WORKSPACE_ROOT = Path("/tmp/codeguide_mini_repo_eval")


def run_command(cmd: str, cwd: str | Path, timeout: int) -> dict[str, Any]:
    normalized_cmd = normalize_test_command(cmd)
    env = os.environ.copy()
    project_root = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = project_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        completed = subprocess.run(
            normalized_cmd,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "normalized_cmd": normalized_cmd,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\nTimed out after {timeout}s",
            "timeout": True,
        }
    return {
        "cmd": cmd,
        "normalized_cmd": normalized_cmd,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timeout": False,
    }


def normalize_test_command(cmd: str) -> str:
    stripped = cmd.strip()
    if stripped.startswith("python -m pytest "):
        return stripped.replace("python -m pytest", "python -m codeguide_agent.testing.simple_pytest", 1)
    if stripped == "python -m pytest":
        return "python -m codeguide_agent.testing.simple_pytest"
    return stripped


def prepare_workspace(task: MiniRepoDebugTask, workspace_root: str | Path) -> Path:
    destination = Path(workspace_root) / task.task_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        task.repo_path,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"),
    )
    run_command("git init -q", destination, timeout=10)
    run_command("git add .", destination, timeout=10)
    run_command('git -c user.email=codeguide@example.local -c user.name=CodeGuide commit -qm "initial task state"', destination, timeout=10)
    return destination


def git_diff(repo_path: str | Path) -> str:
    result = run_command("git diff -- .", repo_path, timeout=10)
    return (result["stdout"] or "") + (result["stderr"] or "")


def evaluate_one(
    task: MiniRepoDebugTask,
    trajectory_dir: str | Path,
    workspace_root: str | Path,
    timeout: int,
) -> dict[str, Any]:
    before_checksum = compute_repo_checksum(task.repo_path)
    workspace = prepare_workspace(task, workspace_root)
    metadata = dict(task.metadata)
    trajectory_path = Path(trajectory_dir) / f"{task.task_id}_forge.jsonl"

    pre_public = run_command(metadata["public_test_cmd"], workspace, timeout=timeout)
    agent_result = run_forge_baseline(
        repo_path=workspace,
        task_id=task.task_id,
        description=task.description,
        public_test_cmd=metadata["public_test_cmd"],
        hidden_test_cmd=metadata["hidden_test_cmd"],
        trajectory_path=trajectory_path,
        timeout=timeout,
    )
    public_result = run_command(metadata["public_test_cmd"], workspace, timeout=timeout)
    hidden_result = run_command(metadata["hidden_test_cmd"], workspace, timeout=timeout)
    diff_text = git_diff(workspace)
    pre_counts = public_test_counts(pre_public)
    post_counts = public_test_counts(public_result)

    patch_metrics = evaluate_patch(
        diff_text=diff_text,
        repo_path=str(workspace),
        gold_files=metadata.get("gold_files", []),
        gold_functions=metadata.get("gold_functions", []),
    )
    regression = post_counts["pass_count"] < pre_counts["pass_count"]
    canonical_reward = calculate_reward(
        public_result,
        hidden_result,
        diff_text,
        regression=regression,
        gold_files=metadata.get("gold_files", []),
        suspicious_files=metadata.get("gold_files", []),
    )
    metrics = {
        "task_id": task.task_id,
        "public_test_pass": public_result["exit_code"] == 0,
        "hidden_test_pass": hidden_result["exit_code"] == 0,
        "regression": regression,
        "pre_public_pass_count": pre_counts["pass_count"],
        "pre_public_fail_count": pre_counts["fail_count"],
        "post_public_pass_count": post_counts["pass_count"],
        "post_public_fail_count": post_counts["fail_count"],
        **patch_metrics,
        **canonical_reward,
    }
    after_checksum = compute_repo_checksum(task.repo_path)
    original_repo_unchanged = before_checksum == after_checksum

    return {
        "task_id": task.task_id,
        "workspace": str(workspace),
        "trajectory_path": str(trajectory_path),
        "agent_result": agent_result,
        "tests": {
            "pre_public": pre_public,
            "public": public_result,
            "hidden": hidden_result,
        },
        "metrics": metrics,
        "original_repo_unchanged": original_repo_unchanged,
        "original_checksum_before": before_checksum,
        "original_checksum_after": after_checksum,
        "safety_error": "" if original_repo_unchanged else "original repository changed during forge baseline comparison",
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"num_tasks": 0}

    def rate(key: str) -> float:
        return round(sum(1 for result in results if result["metrics"].get(key)) / len(results), 4)

    def avg(key: str) -> float:
        return round(sum(float(result["metrics"].get(key, 0)) for result in results) / len(results), 4)

    return {
        "num_tasks": len(results),
        "gold_file_hit_rate": rate("gold_file_hit"),
        "gold_function_hit_rate": rate("gold_function_hit"),
        "public_test_pass_rate": rate("public_test_pass"),
        "hidden_test_pass_rate": rate("hidden_test_pass"),
        "average_patch_size": avg("patch_size"),
        "no_test_deletion_rate": rate("no_test_deletion"),
        "no_hardcode_rate": rate("no_hardcode"),
        "regression_rate": rate("regression"),
        "average_total_reward": avg("total_reward"),
    }


def public_test_counts(result: dict[str, Any] | None) -> dict[str, int]:
    if not result:
        return {"pass_count": 0, "fail_count": 0}
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    pass_count = sum(int(value) for value in re.findall(r"(\d+)\s+passed", text))
    fail_count = sum(int(value) for value in re.findall(r"(\d+)\s+failed", text))
    if pass_count == 0 and fail_count == 0:
        if result.get("exit_code") == 0:
            pass_count = 1
        else:
            fail_count = 1
    return {"pass_count": pass_count, "fail_count": fail_count}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a forge-runtime baseline comparison on Mini-Repo-Debug.")
    parser.add_argument("--tasks", required=True, help="Path to data/mini_repo_debug/tasks.jsonl")
    parser.add_argument("--task-id", help="Optional task id filter")
    parser.add_argument("--trajectory-dir", default=str(DEFAULT_TRAJECTORY_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--workspace-root", default=str(DEFAULT_WORKSPACE_ROOT))
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    tasks = load_tasks(args.tasks, task_id=args.task_id)
    if not tasks:
        print(f"No tasks found in {args.tasks!r}")
        return 1

    Path(args.trajectory_dir).mkdir(parents=True, exist_ok=True)
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    results = [evaluate_one(task, args.trajectory_dir, args.workspace_root, args.timeout) for task in tasks]
    report_path = Path(args.report_dir) / "eval_report.json"
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks_path": str(Path(args.tasks)),
        "summary": summarize(results),
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print("Mini-Repo-Debug Forge Baseline Comparison Summary")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print(f"report_path: {report_path}")
    print(f"trajectory_dir: {Path(args.trajectory_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
