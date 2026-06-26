"""SWE-bench Lite eval adapter — schema, ingestion, test wrapping, result format.

Maps SWE-bench-style task descriptions to the CodeGuide-Agent eval pipeline.
No external API calls — all operations are local.

Design follows SWE-bench evaluation protocol:
  - Each task has: instance_id, repo, problem_statement, FAIL_TO_PASS,
    PASS_TO_PASS, test_patch, gold patch.
  - The agent produces a patch; we apply it and run the test suite.
  - Report: resolved=true if all FAIL_TO_PASS tests pass AND all
    PASS_TO_PASS tests still pass.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# SWE-bench data schemas
# ---------------------------------------------------------------------------


@dataclass
class SWEBenchTask:
    """Single SWE-bench-style task."""

    instance_id: str
    repo_path: str  # path to repo root
    problem_statement: str  # issue / problem description
    base_commit: str = ""
    hints_text: str = ""
    fail_to_pass: list[str] = field(default_factory=list)  # tests that MUST pass after fix
    pass_to_pass: list[str] = field(default_factory=list)  # tests that must STILL pass
    test_patch: str = ""  # diff to apply before testing
    gold_patch: str = ""  # reference solution (for eval only, never shown to agent)
    test_command: str = "python -m pytest tests -q"
    repo_type: str = "local"  # "local" | "github"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SWEBenchTask:
        return cls(
            instance_id=d.get("instance_id", d.get("task_id", "")),
            repo_path=d.get("repo_path", d.get("repo", "")),
            problem_statement=d.get("problem_statement", d.get("issue", "")),
            base_commit=d.get("base_commit", ""),
            hints_text=d.get("hints_text", ""),
            fail_to_pass=d.get("FAIL_TO_PASS", d.get("fail_to_pass", [])),
            pass_to_pass=d.get("PASS_TO_PASS", d.get("pass_to_pass", [])),
            test_patch=d.get("test_patch", ""),
            gold_patch=d.get("gold_patch", d.get("patch", "")),
            test_command=d.get("test_command", "python -m pytest tests -q"),
            repo_type=d.get("repo_type", "local"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "repo_path": self.repo_path,
            "problem_statement": self.problem_statement,
            "base_commit": self.base_commit,
            "hints_text": self.hints_text,
            "FAIL_TO_PASS": self.fail_to_pass,
            "PASS_TO_PASS": self.pass_to_pass,
            "test_patch": self.test_patch,
            "test_command": self.test_command,
            "repo_type": self.repo_type,
        }


@dataclass
class SWEBenchResult:
    """Result of evaluating one agent patch against a SWE-bench task."""

    instance_id: str
    resolved: bool = False
    applied_patch: str = ""
    test_output: str = ""
    fail_to_pass_passed: int = 0
    fail_to_pass_total: int = 0
    pass_to_pass_passed: int = 0
    pass_to_pass_total: int = 0
    error: str = ""
    repo_setup_ok: bool = False
    patch_applied_ok: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "resolved": self.resolved,
            "fail_to_pass": {"passed": self.fail_to_pass_passed, "total": self.fail_to_pass_total},
            "pass_to_pass": {"passed": self.pass_to_pass_passed, "total": self.pass_to_pass_total},
            "repo_setup_ok": self.repo_setup_ok,
            "patch_applied_ok": self.patch_applied_ok,
            "error": self.error,
            "test_output_tail": self.test_output[-2000:] if self.test_output else "",
        }


# ---------------------------------------------------------------------------
# Task loader
# ---------------------------------------------------------------------------


def load_swe_bench_tasks(path: str | Path) -> list[SWEBenchTask]:
    """Load SWE-bench tasks from a JSON or JSONL file."""
    path = Path(path)
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    tasks: list[SWEBenchTask] = []

    # Try JSON array first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            for d in data:
                tasks.append(SWEBenchTask.from_dict(d))
            return tasks
    except (json.JSONDecodeError, TypeError):
        pass

    # Try JSONL
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tasks.append(SWEBenchTask.from_dict(json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue

    return tasks


def convert_mini_repo_task(
    task_dir: str | Path,
    gold_files: list[str] | None = None,
    gold_functions: list[str] | None = None,
) -> SWEBenchTask:
    """Convert a Mini-Repo-Debug task directory to SWE-bench format."""
    task_dir = Path(task_dir)
    task_id = task_dir.name

    # Read issue
    issue_text = ""
    issue_path = task_dir / "issue.md"
    if issue_path.exists():
        issue_text = issue_path.read_text(encoding="utf-8")
    else:
        meta_path = task_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            issue_text = meta.get("issue", meta.get("description", ""))

    # Read gold patch
    gold_patch = ""
    gp_path = task_dir / "gold.patch"
    if gp_path.exists():
        gold_patch = gp_path.read_text(encoding="utf-8")

    # Find test files
    test_dir = task_dir / "tests"
    fail_to_pass: list[str] = []
    pass_to_pass: list[str] = []
    if test_dir.is_dir():
        for tf in sorted(test_dir.glob("test_*.py")):
            test_mod = tf.stem
            # Extract test function names (simple heuristic)
            content = tf.read_text(encoding="utf-8")
            import re
            funcs = re.findall(r"def (test_\w+)", content)
            for f in funcs:
                pass_to_pass.append(f"{test_mod}::{f}")

    return SWEBenchTask(
        instance_id=task_id,
        repo_path=str(task_dir),
        problem_statement=issue_text,
        base_commit="",
        hints_text="",
        fail_to_pass=fail_to_pass,
        pass_to_pass=pass_to_pass,
        test_patch="",
        gold_patch=gold_patch,
        test_command="python -m pytest tests -q",
        repo_type="local",
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_swe_task(
    task: SWEBenchTask,
    agent_patch: str,
    timeout: int = 120,
) -> SWEBenchResult:
    """Evaluate an agent patch against a SWE-bench task.

    Args:
        task: The SWE-bench task definition.
        agent_patch: The unified diff produced by the agent.
        timeout: Test command timeout in seconds.

    Returns:
        SWEBenchResult with resolved status and detailed metrics.
    """
    result = SWEBenchResult(instance_id=task.instance_id)
    result.applied_patch = agent_patch

    repo_path = Path(task.repo_path)
    if not repo_path.is_dir():
        result.error = f"repo not found: {repo_path}"
        return result

    result.repo_setup_ok = True

    # Work in a temp copy to avoid polluting the original
    with tempfile.TemporaryDirectory(prefix="swebench_eval_") as tmp:
        tmp_path = Path(tmp) / task.instance_id
        _copy_dir(repo_path, tmp_path)

        # Apply test patch if provided
        if task.test_patch:
            try:
                _apply_patch(tmp_path, task.test_patch)
            except Exception as exc:
                result.error = f"test_patch apply failed: {exc}"
                return result

        # Apply agent patch
        if agent_patch.strip():
            try:
                _apply_patch(tmp_path, agent_patch)
                result.patch_applied_ok = True
            except Exception as exc:
                result.error = f"agent patch apply failed: {exc}"
                return result
        else:
            result.error = "empty agent patch"
            return result

        # Run test command
        test_output, returncode = _run_test(tmp_path, task.test_command, timeout)
        result.test_output = test_output

        # Parse test results
        if task.fail_to_pass:
            ftp_passed = 0
            for tc in task.fail_to_pass:
                if _test_passed(test_output, tc):
                    ftp_passed += 1
            result.fail_to_pass_passed = ftp_passed
            result.fail_to_pass_total = len(task.fail_to_pass)

        if task.pass_to_pass:
            ptp_passed = 0
            for tc in task.pass_to_pass:
                if _test_passed(test_output, tc):
                    ptp_passed += 1
            result.pass_to_pass_passed = ptp_passed
            result.pass_to_pass_total = len(task.pass_to_pass)

        # Resolved: all fail_to_pass pass, all pass_to_pass still pass
        ftp_ok = result.fail_to_pass_passed == result.fail_to_pass_total if task.fail_to_pass else returncode == 0
        ptp_ok = result.pass_to_pass_passed == result.pass_to_pass_total if task.pass_to_pass else True
        result.resolved = ftp_ok and ptp_ok

    return result


def evaluate_batch(
    tasks: list[SWEBenchTask],
    patches: dict[str, str],  # instance_id -> diff text
    timeout: int = 120,
) -> dict[str, Any]:
    """Evaluate a batch of tasks and return aggregate report.

    Returns a dict compatible with SWE-bench eval reporting.
    """
    results: list[SWEBenchResult] = []
    for task in tasks:
        patch = patches.get(task.instance_id, "")
        r = evaluate_swe_task(task, patch, timeout=timeout)
        results.append(r)

    resolved = sum(1 for r in results if r.resolved)
    total = len(results)
    errors = [r for r in results if r.error]

    return {
        "total": total,
        "resolved": resolved,
        "unresolved": total - resolved,
        "error_count": len(errors),
        "resolve_rate": round(resolved / max(1, total), 4),
        "results": [r.to_dict() for r in results],
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _copy_dir(src: Path, dst: Path) -> None:
    """Copy directory tree, skipping caches."""
    import shutil
    ignore = shutil.ignore_patterns("__pycache__", ".git", ".pytest_cache", "*.pyc")
    shutil.copytree(str(src), str(dst), ignore=ignore, dirs_exist_ok=True)


def _apply_patch(repo_path: Path, patch_text: str) -> None:
    """Apply a unified diff patch to the repo."""
    proc = subprocess.run(
        ["patch", "-p1", "--no-backup-if-mismatch", "--force"],
        input=patch_text,
        text=True,
        capture_output=True,
        cwd=str(repo_path),
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"patch failed: {proc.stderr[:500]}")


def _normalize_test_command(command: str) -> str:
    """Normalize test command to use project's simple_pytest runner."""
    stripped = command.strip()
    if stripped.startswith("python -m pytest "):
        return stripped.replace("python -m pytest", "python -m codeguide_agent.testing.simple_pytest", 1)
    if stripped == "python -m pytest":
        return "python -m codeguide_agent.testing.simple_pytest"
    if stripped.startswith("pytest "):
        return stripped.replace("pytest", "python -m codeguide_agent.testing.simple_pytest", 1)
    if stripped == "pytest":
        return "python -m codeguide_agent.testing.simple_pytest"
    return stripped


def _run_test(repo_path: Path, command: str, timeout: int) -> tuple[str, int]:
    """Run test command and return (output, returncode)."""
    import os
    import shlex
    import sys as _sys
    command = _normalize_test_command(command)
    try:
        args = shlex.split(command)
    except ValueError:
        args = command.split()
    # Use the same Python that's running this code
    if args and args[0] in ("python", "python3"):
        args[0] = _sys.executable
    # Add project root to PYTHONPATH so codeguide_agent is importable from temp dirs
    env = os.environ.copy()
    project_root = str(Path(__file__).resolve().parents[2])
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing}" if existing else project_root
    proc = subprocess.run(
        args,
        text=True,
        capture_output=True,
        cwd=str(repo_path),
        timeout=timeout,
        check=False,
        env=env,
    )
    return proc.stdout + "\n" + proc.stderr, proc.returncode


def _test_passed(test_output: str, test_id: str) -> bool:
    """Check if a specific test passed in the output.

    test_id format: "test_module::test_function" or just "test_function"
    """
    # Simple heuristic: test output contains "PASSED" or no "FAILED" for this test
    test_name = test_id.split("::")[-1] if "::" in test_id else test_id
    # Look for "test_name PASSED" or absence of "test_name FAILED"
    if f"{test_name} PASSED" in test_output:
        return True
    if f"{test_name} FAILED" in test_output:
        return False
    # If not explicitly mentioned, check overall pass
    if " passed" in test_output and " failed" not in test_output:
        return True
    # Check pytest summary
    if "= " in test_output and " failed" not in test_output.split("= ")[-1]:
        pass
    return False
