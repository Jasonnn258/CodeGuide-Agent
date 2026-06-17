from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.schemas import load_metadata
from codeguide_agent.reward.calculator import calculate_reward
from codeguide_agent.tools.git_diff import git_diff
from codeguide_agent.tools.read_file import read_file
from codeguide_agent.tools.repo_tree import repo_tree
from codeguide_agent.tools.run_test import run_test
from codeguide_agent.tools.search_repo import search_repo
from codeguide_agent.trajectory.logger import TrajectoryLogger


def _apply_gold_patch(repo_path: Path) -> dict[str, Any]:
    patch_path = repo_path / "gold.patch"
    proc = subprocess.run(["git", "apply", str(patch_path)], cwd=repo_path, text=True, capture_output=True)
    return {
        "tool_name": "apply_gold_patch",
        "status": "success" if proc.returncode == 0 else "error",
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_baseline(
    task_dir: str | Path,
    mode: str = "noop",
    trajectories_dir: str | Path = "data/mini_repo_debug/trajectories",
    timeout: int = 30,
    run_hidden: bool = False,
) -> dict[str, Any]:
    repo_path = Path(task_dir)
    metadata = load_metadata(repo_path)
    task_id = metadata["task_id"]
    logger = TrajectoryLogger(
        Path(trajectories_dir) / f"{task_id}_{mode}.jsonl",
        task_id=task_id,
        trajectory_id=f"{task_id}_{mode}",
        model=f"prompt_only_{mode}",
    )

    tree = repo_tree(repo_path)
    logger.log_step("repo_tree", {"max_depth": 4}, tree, "Inspect repository structure.")

    query = metadata["gold_functions"][0] if metadata.get("gold_functions") else metadata["bug_type"]
    search = search_repo(repo_path, query, file_glob="*.py")
    logger.log_step("search_repo", {"query": query, "file_glob": "*.py"}, search, "Search for likely repair locations.")

    if metadata.get("gold_files"):
        read = read_file(repo_path, metadata["gold_files"][0])
        logger.log_step("read_file", {"file_path": metadata["gold_files"][0]}, read, "Read one likely source file.")

    if mode == "gold":
        patch_result = _apply_gold_patch(repo_path)
        logger.log_step("apply_gold_patch", {"patch": "gold.patch"}, patch_result, "Apply handcrafted gold patch simulation.")
    else:
        noop = {"tool_name": "noop", "status": "success", "message": "No edit made in noop mode."}
        logger.log_step("noop", {}, noop, "Phase 1 deterministic no-op baseline.")

    public_result = run_test(repo_path, metadata["public_test_cmd"], timeout=timeout)
    logger.log_step("run_test", {"command": metadata["public_test_cmd"]}, public_result, "Run public verifier.")

    if run_hidden:
        hidden_result = run_test(repo_path, metadata["hidden_test_cmd"], timeout=timeout)
        logger.log_step("run_test", {"command": metadata["hidden_test_cmd"]}, hidden_result, "Run hidden verifier.")
    else:
        hidden_result = None
        logger.log_step(
            "skip_hidden_tests",
            {"run_hidden": False},
            {"tool_name": "skip_hidden_tests", "status": "success"},
            "Hidden verifier skipped by eval configuration.",
        )

    diff = git_diff(repo_path)
    if mode == "gold" and not diff.get("diff"):
        diff["diff"] = (repo_path / "gold.patch").read_text(encoding="utf-8")
    logger.log_step("git_diff", {}, diff, "Collect final patch diff.")

    reward = calculate_reward(
        public_result,
        hidden_result,
        diff.get("diff", ""),
        gold_files=metadata.get("gold_files", []),
        suspicious_files=metadata.get("gold_files", []),
    )
    final_status = "success" if reward["public_pass"] and reward["hidden_pass"] else "fail"
    logger.log_final(diff.get("diff", ""), reward, final_status)

    return {"task_id": task_id, "reward": reward, "tool_calls": logger.step_count, "trajectory": str(logger.path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic prompt-only baseline.")
    parser.add_argument("task_dir")
    parser.add_argument("--mode", choices=["noop", "gold"], default="noop")
    parser.add_argument("--trajectories-dir", default="data/mini_repo_debug/trajectories")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--run-hidden", action="store_true")
    args = parser.parse_args()
    result = run_baseline(
        args.task_dir,
        mode=args.mode,
        trajectories_dir=args.trajectories_dir,
        timeout=args.timeout,
        run_hidden=args.run_hidden,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
