from __future__ import annotations

from pathlib import Path
import os
import subprocess

from codeguide_agent.tools.common import resolve_repo_path


def run_test(repo_path: str | Path, command: str, timeout: int = 30) -> dict:
    root = resolve_repo_path(repo_path)
    normalized_command = _normalize_test_command(command)
    env = os.environ.copy()
    project_root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = project_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        proc = subprocess.run(normalized_command, cwd=root, shell=True, text=True, capture_output=True, timeout=timeout, env=env)
        return {
            "tool_name": "run_test",
            "status": "success",
            "command": command,
            "normalized_command": normalized_command,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timeout": timeout,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "tool_name": "run_test",
            "status": "timeout",
            "command": command,
            "normalized_command": normalized_command,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": timeout,
        }
    except Exception as exc:
        return {"tool_name": "run_test", "status": "error", "command": command, "normalized_command": normalized_command, "exit_code": 1, "stdout": "", "stderr": str(exc)}


def _normalize_test_command(command: str) -> str:
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
