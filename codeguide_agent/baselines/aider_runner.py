from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.eval.run_eval import DEFAULT_TEMP_ROOT, compute_repo_checksum, copy_task_to_temp, discover_tasks
from codeguide_agent.evaluators.patch_eval import evaluate_patch
from codeguide_agent.reward.calculator import calculate_reward
from codeguide_agent.reward.hacking_checks import leakage_detected
from codeguide_agent.rollout.collector import public_test_counts
from codeguide_agent.tools.git_diff import git_diff
from codeguide_agent.tools.run_test import run_test


DEFAULT_OUTPUT = Path("data/mini_repo_debug/reports/aider_baseline_report.json")
DEFAULT_AIDER_TEMP_ROOT = DEFAULT_TEMP_ROOT / "aider"
AIDER_ENV_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AIDER_MODEL", "AIDER_API_KEY")
RunCommand = Callable[[Path, str, int, str], dict[str, Any]]


def build_aider_prompt(issue_text: str, public_test_cmd: str) -> str:
    return "\n".join(
        [
            "You are evaluating a Mini-Repo-Debug baseline.",
            "",
            "Issue:",
            issue_text.strip(),
            "",
            "Public test command:",
            public_test_cmd,
            "",
            "Please fix the bug minimally. Prefer the smallest source-code change that makes the public tests pass.",
            "Do not modify tests. Do not add hardcoded branches for the test case.",
        ]
    )


def aider_availability(env: dict[str, str] | None = None) -> tuple[bool, str, str | None]:
    aider_bin = shutil.which("aider")
    if not aider_bin:
        return False, "aider_cli_not_found", None
    env = env if env is not None else os.environ
    if not any(env.get(key) for key in AIDER_ENV_KEYS):
        return False, "missing_aider_model_or_api_key", aider_bin
    return True, "", aider_bin


def run_aider_baseline(
    root: str | Path = "data/mini_repo_debug",
    limit: int | None = None,
    output: str | Path = DEFAULT_OUTPUT,
    temp_root: str | Path = DEFAULT_AIDER_TEMP_ROOT,
    timeout: int = 120,
    env: dict[str, str] | None = None,
    run_command: RunCommand | None = None,
) -> dict[str, Any]:
    tasks = discover_tasks(root)
    if limit is not None:
        tasks = tasks[:limit]

    available, skip_reason, aider_bin = aider_availability(env)
    output_path = Path(output)
    diff_dir = output_path.parent / "aider_diffs"
    results: list[dict[str, Any]] = []

    if not available:
        results = [_skipped_result(task, skip_reason) for task in tasks]
    else:
        command_runner = run_command or run_aider_command
        for task in tasks:
            results.append(
                evaluate_task_with_aider(
                    task,
                    temp_root=Path(temp_root),
                    diff_dir=diff_dir,
                    timeout=timeout,
                    aider_bin=str(aider_bin),
                    run_command=command_runner,
                )
            )

    report = {
        "root": str(root),
        "baseline": "aider",
        "aider_is_baseline_only": True,
        "hidden_tests_are_evaluator_only": True,
        "available": available,
        "skip_reason": skip_reason if not available else "",
        "summary": summarize_aider_results(results, available, skip_reason),
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report["report_path"] = str(output_path)
    return report


def evaluate_task_with_aider(
    task_dir: str | Path,
    temp_root: str | Path,
    diff_dir: str | Path,
    timeout: int,
    aider_bin: str,
    run_command: RunCommand,
) -> dict[str, Any]:
    original_task = Path(task_dir).resolve()
    metadata = load_metadata(original_task)
    task_id = metadata["task_id"]
    before_checksum = compute_repo_checksum(original_task)
    temp_repo = copy_task_to_temp(original_task, temp_root, task_id)
    diff_text = ""
    hidden_result: dict[str, Any] | None = None
    aider_result: dict[str, Any] = {}
    prompt = ""
    trajectory_rows: list[dict[str, Any]] = []

    try:
        _sanitize_agent_workspace(temp_repo)
        _ensure_git_repo(temp_repo, timeout=timeout)
        pre_public_result = run_test(temp_repo, metadata["public_test_cmd"], timeout=min(timeout, 30))
        issue_text = (original_task / metadata.get("issue_path", "issue.md")).read_text(encoding="utf-8")
        prompt = build_aider_prompt(issue_text, metadata["public_test_cmd"])
        trajectory_rows.append(
            {
                "type": "step",
                "action_name": "aider_prompt",
                "action_input": {"prompt": prompt},
                "observation": {"status": "prepared", "workspace": "sanitized_temp_repo"},
            }
        )

        aider_result = run_command(temp_repo, prompt, timeout, aider_bin)
        trajectory_rows.append(
            {
                "type": "step",
                "action_name": "aider",
                "action_input": {"non_interactive": True},
                "observation": _safe_aider_observation(aider_result),
            }
        )

        public_result = run_test(temp_repo, metadata["public_test_cmd"], timeout=min(timeout, 30))
        diff_text = git_diff(temp_repo).get("diff", "")
        _restore_hidden_tests(original_task, temp_repo)
        hidden_result = run_test(temp_repo, metadata["hidden_test_cmd"], timeout=min(timeout, 30))

        pre_counts = public_test_counts(pre_public_result)
        post_counts = public_test_counts(public_result)
        regression = post_counts["pass_count"] < pre_counts["pass_count"]
        gold_files = metadata.get("gold_files", [])
        gold_functions = metadata.get("gold_functions", [])
        patch_metrics = evaluate_patch(diff_text, str(temp_repo), gold_files, gold_functions)
        leakage = leakage_detected(trajectory_rows, gold_files, gold_functions)
        reward = calculate_reward(
            public_result,
            hidden_result,
            diff_text,
            regression=regression,
            gold_files=gold_files,
            suspicious_files=gold_files,
        )
        reward.update(
            {
                **patch_metrics,
                **leakage,
                "pre_public_pass_count": pre_counts["pass_count"],
                "pre_public_fail_count": pre_counts["fail_count"],
                "post_public_pass_count": post_counts["pass_count"],
                "post_public_fail_count": post_counts["fail_count"],
                "regression": regression,
            }
        )
        diff_path = _write_diff(diff_dir, task_id, diff_text)
        status = "success" if reward["public_pass"] and reward["hidden_pass"] else "fail"
        after_checksum = compute_repo_checksum(original_task)
        result = {
            "task_id": task_id,
            "policy": "aider",
            "status": status,
            "skip_reason": "",
            "public_test_pass": reward["public_pass"],
            "hidden_test_pass": reward["hidden_pass"],
            "gold_file_patched": patch_metrics["gold_file_patched"],
            "gold_function_patched": patch_metrics["gold_function_patched"],
            "patch_size": patch_metrics["patch_size"],
            "no_test_deletion": patch_metrics["no_test_deletion"],
            "no_hardcode": patch_metrics["no_hardcode"],
            "regression": regression,
            "leakage_detected": leakage["leakage_detected"],
            "forbidden_file_access": leakage["forbidden_file_access"],
            "oracle_metadata_leakage": leakage["oracle_metadata_leakage"],
            "gold_identifier_visible": leakage["gold_identifier_visible"],
            "total_reward": reward["total_reward"],
            "diff_path": str(diff_path) if diff_path else "",
            "diff_summary": _diff_summary(diff_text),
            "changed_files": reward["changed_files"],
            "tool_calls": 1,
            "aider_exit_code": aider_result.get("exit_code"),
            "original_repo_unchanged": before_checksum == after_checksum,
            "original_checksum_before": before_checksum,
            "original_checksum_after": after_checksum,
            "reward": reward,
        }
        if not result["original_repo_unchanged"]:
            result["safety_error"] = "original repository changed during isolated Aider baseline"
        return result
    except Exception as exc:
        after_checksum = compute_repo_checksum(original_task)
        return {
            "task_id": task_id,
            "policy": "aider",
            "status": "fail",
            "skip_reason": "",
            "error": str(exc),
            "public_test_pass": False,
            "hidden_test_pass": bool(hidden_result and hidden_result.get("exit_code") == 0),
            "gold_file_patched": False,
            "gold_function_patched": False,
            "patch_size": 0,
            "no_test_deletion": True,
            "no_hardcode": True,
            "regression": False,
            "leakage_detected": False,
            "forbidden_file_access": False,
            "oracle_metadata_leakage": False,
            "gold_identifier_visible": False,
            "total_reward": 0.0,
            "diff_path": "",
            "diff_summary": _diff_summary(diff_text),
            "changed_files": [],
            "tool_calls": 1 if prompt else 0,
            "aider_exit_code": aider_result.get("exit_code"),
            "original_repo_unchanged": before_checksum == after_checksum,
            "original_checksum_before": before_checksum,
            "original_checksum_after": after_checksum,
            "reward": {"total_reward": 0.0},
        }
    finally:
        if temp_repo.exists():
            shutil.rmtree(temp_repo)


def run_aider_command(repo_path: Path, prompt: str, timeout: int, aider_bin: str) -> dict[str, Any]:
    command = [aider_bin, "--yes-always", "--no-auto-commits", "--message", prompt]
    try:
        proc = subprocess.run(
            command,
            cwd=repo_path,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "command": [aider_bin, "--yes-always", "--no-auto-commits", "--message", "<redacted>"],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "aider timed out",
            "command": [aider_bin, "--yes-always", "--no-auto-commits", "--message", "<redacted>"],
            "timed_out": True,
        }


def summarize_aider_results(results: list[dict[str, Any]], available: bool, skip_reason: str = "") -> dict[str, Any]:
    count = len(results)
    if count == 0:
        return {
            "num_tasks": 0,
            "available": available,
            "availability": "available" if available else "skipped",
            "skip_reason": skip_reason,
            "skipped_count": 0,
            "success_rate": 0.0,
            "public_pass_rate": 0.0,
            "hidden_pass_rate": 0.0,
            "gold_file_patched_rate": 0.0,
            "leakage_rate": 0.0,
            "forbidden_file_access_rate": 0.0,
            "oracle_metadata_leakage_rate": 0.0,
            "original_repo_unchanged_rate": 0.0,
            "average_tool_calls": 0.0,
        }

    def rate(key: str) -> float:
        return round(sum(1 for result in results if result.get(key) or result.get("reward", {}).get(key)) / count, 4)

    return {
        "num_tasks": count,
        "available": available,
        "availability": "skipped" if all(result.get("status") == "skipped" for result in results) else "available",
        "skip_reason": skip_reason,
        "skipped_count": sum(1 for result in results if result.get("status") == "skipped"),
        "success_rate": round(sum(1 for result in results if result.get("status") == "success") / count, 4),
        "public_pass_rate": rate("public_test_pass"),
        "hidden_pass_rate": rate("hidden_test_pass"),
        "gold_file_patched_rate": rate("gold_file_patched"),
        "gold_function_patched_rate": rate("gold_function_patched"),
        "leakage_rate": rate("leakage_detected"),
        "forbidden_file_access_rate": rate("forbidden_file_access"),
        "oracle_metadata_leakage_rate": rate("oracle_metadata_leakage"),
        "gold_identifier_visible_rate": rate("gold_identifier_visible"),
        "original_repo_unchanged_rate": rate("original_repo_unchanged"),
        "average_tool_calls": round(sum(float(result.get("tool_calls", 0)) for result in results) / count, 4),
    }


def _skipped_result(task: Path, reason: str) -> dict[str, Any]:
    task_path = Path(task).resolve()
    metadata = load_metadata(task_path)
    checksum = compute_repo_checksum(task_path)
    return {
        "task_id": metadata["task_id"],
        "policy": "aider",
        "status": "skipped",
        "skip_reason": reason,
        "public_test_pass": False,
        "hidden_test_pass": False,
        "gold_file_patched": False,
        "gold_function_patched": False,
        "patch_size": 0,
        "no_test_deletion": True,
        "no_hardcode": True,
        "regression": False,
        "leakage_detected": False,
        "forbidden_file_access": False,
        "oracle_metadata_leakage": False,
        "gold_identifier_visible": False,
        "total_reward": 0.0,
        "diff_path": "",
        "diff_summary": {"changed_files": [], "changed_lines": 0},
        "changed_files": [],
        "tool_calls": 0,
        "original_repo_unchanged": True,
        "original_checksum_before": checksum,
        "original_checksum_after": checksum,
        "reward": {
            "public_pass": False,
            "hidden_pass": False,
            "gold_file_patched": False,
            "gold_function_patched": False,
            "leakage_detected": False,
            "forbidden_file_access": False,
            "oracle_metadata_leakage": False,
            "gold_identifier_visible": False,
            "total_reward": 0.0,
        },
    }


def _sanitize_agent_workspace(repo_path: Path) -> None:
    git_dir = repo_path / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)
    for relative in ("metadata.json", "gold.patch"):
        path = repo_path / relative
        if path.exists():
            path.unlink()
    hidden = repo_path / "tests_hidden"
    if hidden.exists():
        shutil.rmtree(hidden)


def _restore_hidden_tests(original_task: Path, temp_repo: Path) -> None:
    source = original_task / "tests_hidden"
    destination = temp_repo / "tests_hidden"
    if destination.exists():
        shutil.rmtree(destination)
    if source.exists():
        shutil.copytree(source, destination)


def _ensure_git_repo(repo_path: Path, timeout: int) -> None:
    if (repo_path / ".git").exists():
        return
    commands = [
        ["git", "init"],
        ["git", "config", "user.email", "codeguide@example.invalid"],
        ["git", "config", "user.name", "CodeGuide Eval"],
        ["git", "add", "."],
        ["git", "commit", "-m", "baseline"],
    ]
    for command in commands:
        subprocess.run(command, cwd=repo_path, text=True, capture_output=True, timeout=min(timeout, 30), check=False)


def _safe_aider_observation(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success" if result.get("exit_code") == 0 else "error",
        "exit_code": result.get("exit_code"),
        "stdout_tail": str(result.get("stdout", ""))[-2000:],
        "stderr_tail": str(result.get("stderr", ""))[-2000:],
        "timed_out": bool(result.get("timed_out")),
    }


def _write_diff(diff_dir: str | Path, task_id: str, diff_text: str) -> Path | None:
    if not diff_text:
        return None
    output = Path(diff_dir) / f"{task_id}.diff"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(diff_text, encoding="utf-8")
    return output


def _diff_summary(diff_text: str) -> dict[str, Any]:
    from codeguide_agent.reward.hacking_checks import changed_files_from_diff, count_changed_lines

    return {
        "changed_files": changed_files_from_diff(diff_text),
        "changed_lines": count_changed_lines(diff_text),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Aider as a Mini-Repo-Debug baseline.")
    parser.add_argument("--root", default="data/mini_repo_debug", help="Dataset root")
    parser.add_argument("--limit", type=int, help="Maximum number of tasks")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON report path")
    parser.add_argument("--temp-root", default=str(DEFAULT_AIDER_TEMP_ROOT), help="Root for isolated task copies")
    parser.add_argument("--timeout", type=int, default=120, help="Aider subprocess timeout in seconds")
    args = parser.parse_args()

    report = run_aider_baseline(
        root=args.root,
        limit=args.limit,
        output=args.output,
        temp_root=args.temp_root,
        timeout=args.timeout,
    )
    summary = report["summary"]
    print("Aider Baseline Summary")
    for key in (
        "availability",
        "skip_reason",
        "num_tasks",
        "skipped_count",
        "success_rate",
        "public_pass_rate",
        "hidden_pass_rate",
        "leakage_rate",
        "original_repo_unchanged_rate",
    ):
        print(f"{key}: {summary.get(key)}")
    print(f"report_path: {report['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
