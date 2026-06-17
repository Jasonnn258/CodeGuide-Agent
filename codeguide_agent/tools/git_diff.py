from __future__ import annotations

from pathlib import Path
import subprocess

from codeguide_agent.tools.common import resolve_repo_path


def git_diff(repo_path: str | Path) -> dict:
    root = resolve_repo_path(repo_path)
    proc = subprocess.run(["git", "diff", "--"], cwd=root, text=True, capture_output=True)
    if proc.returncode != 0 and "Not a git repository" in proc.stderr:
        return {
            "tool_name": "git_diff",
            "status": "success",
            "exit_code": 0,
            "diff": "",
            "stderr": proc.stderr,
        }
    return {
        "tool_name": "git_diff",
        "status": "success" if proc.returncode == 0 else "error",
        "exit_code": proc.returncode,
        "diff": proc.stdout,
        "stderr": proc.stderr,
    }
