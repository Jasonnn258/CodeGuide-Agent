from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

from codeguide_agent.baselines.prompt_only import run_baseline
from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.eval.metrics import summarize_metrics


DEFAULT_TEMP_ROOT = Path("/tmp/codeguide_eval")
DEV_INSTALL_MESSAGE = "pytest is required for Mini-Repo-Debug evaluation. Run: pip install -e .[dev]"


def discover_tasks(root: str | Path, task_id: str | None = None) -> list[Path]:
    root_path = Path(root)
    tasks_jsonl = root_path / "tasks.jsonl"
    if tasks_jsonl.exists():
        tasks: list[Path] = []
        for line in tasks_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if task_id and row.get("task_id") != task_id:
                continue
            repo_path = Path(row["repo_path"])
            tasks.append(repo_path if repo_path.is_absolute() else Path.cwd() / repo_path)
        return tasks

    tasks = sorted(path for path in (root_path / "repos").iterdir() if path.is_dir())
    if task_id:
        tasks = [path for path in tasks if path.name == task_id]
    return tasks


def compute_repo_checksum(repo_path: str | Path) -> str:
    root = Path(repo_path)
    digest = hashlib.sha256()
    ignored_dirs = {"__pycache__", ".pytest_cache", ".codeguide_checkpoints"}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in ignored_dirs for part in relative.parts):
            continue
        digest.update(str(relative).encode("utf-8"))
        if path.is_file():
            digest.update(b"\0file\0")
            digest.update(path.read_bytes())
        elif path.is_dir():
            digest.update(b"\0dir\0")
    return digest.hexdigest()


def copy_task_to_temp(task_dir: str | Path, temp_root: str | Path, task_id: str) -> Path:
    destination = Path(temp_root) / task_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        task_dir,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".codeguide_checkpoints"),
    )
    return destination


def pytest_required(tasks: list[Path], run_hidden: bool) -> bool:
    for task in tasks:
        metadata = load_metadata(task)
        commands = [metadata.get("public_test_cmd", "")]
        if run_hidden:
            commands.append(metadata.get("hidden_test_cmd", ""))
        if any("pytest" in command for command in commands):
            return True
    return False


def pytest_available() -> bool:
    return importlib.util.find_spec("pytest") is not None or importlib.util.find_spec("codeguide_agent.testing.simple_pytest") is not None


def evaluate_task(
    task_dir: str | Path,
    mode: str,
    trajectories_dir: str | Path,
    timeout: int,
    run_hidden: bool,
    temp_root: str | Path = DEFAULT_TEMP_ROOT,
    keep_temp: bool = False,
) -> dict[str, Any]:
    original_task_path = Path(task_dir).resolve()
    metadata = load_metadata(original_task_path)
    task_id = metadata["task_id"]
    before_checksum = compute_repo_checksum(original_task_path)
    temp_task_path = copy_task_to_temp(original_task_path, temp_root, task_id)

    try:
        baseline = run_baseline(
            temp_task_path,
            mode=mode,
            trajectories_dir=trajectories_dir,
            timeout=timeout,
            run_hidden=run_hidden,
        )
        reward = dict(baseline["reward"])
        reward["task_id"] = task_id
        reward["tool_calls"] = baseline["tool_calls"]
        reward["temp_repo_path"] = str(temp_task_path)
        reward["run_hidden"] = run_hidden
    finally:
        if not keep_temp and temp_task_path.exists():
            shutil.rmtree(temp_task_path)

    after_checksum = compute_repo_checksum(original_task_path)
    unchanged = before_checksum == after_checksum
    reward["original_repo_unchanged"] = unchanged
    reward["original_checksum_before"] = before_checksum
    reward["original_checksum_after"] = after_checksum
    if not unchanged:
        reward["safety_error"] = "original repository changed during isolated evaluation"
    return reward


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated Phase 1 Mini-Repo-Debug evaluation.")
    parser.add_argument("--root", default="data/mini_repo_debug", help="Dataset root")
    parser.add_argument("--mode", choices=["noop", "gold"], default="noop", help="Baseline mode")
    parser.add_argument("--task-id", help="Run one task id, e.g. task_001")
    parser.add_argument("--run-hidden", action="store_true", help="Run hidden tests in addition to public tests")
    parser.add_argument("--temp-root", default=str(DEFAULT_TEMP_ROOT), help="Root for isolated task copies")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temp task copies after eval")
    parser.add_argument("--trajectories-dir", default="data/mini_repo_debug/trajectories", help="Where to write JSONL trajectories")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    tasks = discover_tasks(args.root, task_id=args.task_id)
    if not tasks:
        print(f"No tasks found for root={args.root!r} task_id={args.task_id!r}")
        return 1

    if pytest_required(tasks, args.run_hidden) and not pytest_available():
        print(DEV_INSTALL_MESSAGE)
        return 2

    results = [
        evaluate_task(
            task,
            mode=args.mode,
            trajectories_dir=args.trajectories_dir,
            timeout=args.timeout,
            run_hidden=args.run_hidden,
            temp_root=args.temp_root,
            keep_temp=args.keep_temp,
        )
        for task in tasks
    ]
    summary = summarize_metrics(results)
    output = {"summary": summary, "results": results}
    safety_failed = any(not result.get("original_repo_unchanged") for result in results)

    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("Phase 1 Evaluation Summary")
        for key, value in summary.items():
            print(f"{key}: {value}")
        if safety_failed:
            print("SAFETY FAILURE: at least one original repository changed during eval")

    return 1 if safety_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
