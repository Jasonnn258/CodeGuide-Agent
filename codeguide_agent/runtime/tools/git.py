from __future__ import annotations

from pathlib import Path
from typing import Any

from codeguide_agent.runtime.tools.base import ToolResult
from codeguide_agent.runtime.tools.shell import ShellTool


class GitDiffTool(ShellTool):
    name = "git_diff"

    def __init__(self, repo_path: str | Path) -> None:
        super().__init__(repo_path, default_timeout=10)

    def execute(self, params: dict[str, Any]) -> ToolResult:
        return super().execute({"cmd": "git diff -- .", "timeout": params.get("timeout", 10), "cwd": self.repo_path})
