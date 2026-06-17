from __future__ import annotations

from pathlib import Path
import subprocess

from codeguide_agent.tools.common import resolve_repo_path


def run_test(repo_path: str | Path, command: str, timeout: int = 30) -> dict:
    root = resolve_repo_path(repo_path)
    try:
        proc = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, timeout=timeout)
        return {
            "tool_name": "run_test",
            "status": "success",
            "command": command,
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
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": timeout,
        }
    except Exception as exc:
        return {"tool_name": "run_test", "status": "error", "command": command, "exit_code": 1, "stdout": "", "stderr": str(exc)}
