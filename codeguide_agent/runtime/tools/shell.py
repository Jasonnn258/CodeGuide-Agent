from __future__ import annotations

import subprocess
import os
from pathlib import Path
from typing import Any

from codeguide_agent.runtime.tools.base import BaseTool, ToolResult


MAX_OUTPUT_CHARS = 12_000
BLOCKED_SUBSTRINGS = (
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    "git reset --hard",
    "git clean -fd",
    "shutdown",
    "reboot",
)


def truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.6)
    return text[:head] + f"\n...[{len(text) - max_chars} chars truncated]...\n" + text[-(max_chars - head):]


class ShellTool(BaseTool):
    name = "shell"

    def __init__(self, repo_path: str | Path, default_timeout: int = 30) -> None:
        self.repo_path = Path(repo_path)
        self.default_timeout = default_timeout

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cmd = _normalize_command(str(params.get("cmd", "")).strip())
        timeout = int(params.get("timeout", self.default_timeout))
        cwd = Path(params.get("cwd") or self.repo_path)
        if not cmd:
            return ToolResult(False, "", "cmd is required")
        lowered = cmd.lower()
        for blocked in BLOCKED_SUBSTRINGS:
            if blocked in lowered:
                return ToolResult(False, "", f"blocked destructive command: {blocked}")
        try:
            completed = subprocess.run(
                cmd,
                cwd=cwd,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
                env=_runtime_env(),
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            return ToolResult(False, truncate_output(output), f"command timed out after {timeout}s", True)
        output = truncate_output((completed.stdout or "") + (completed.stderr or ""))
        return ToolResult(completed.returncode == 0, output, None if completed.returncode == 0 else f"exit code {completed.returncode}")


def _normalize_command(cmd: str) -> str:
    if cmd.startswith("python -m pytest "):
        return cmd.replace("python -m pytest", "python -m codeguide_agent.testing.simple_pytest", 1)
    if cmd == "python -m pytest":
        return "python -m codeguide_agent.testing.simple_pytest"
    return cmd


def _runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    project_root = str(Path(__file__).resolve().parents[3])
    env["PYTHONPATH"] = project_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env
