from __future__ import annotations

from pathlib import Path
from typing import Any

from codeguide_agent.runtime.tools.base import ToolResult
from codeguide_agent.runtime.tools.shell import ShellTool


class TestTool(ShellTool):
    name = "test"

    def __init__(self, repo_path: str | Path, default_timeout: int = 30) -> None:
        super().__init__(repo_path, default_timeout)

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cmd = str(params.get("cmd", "python -m pytest tests")).strip()
        return super().execute({"cmd": cmd, "timeout": params.get("timeout", self.default_timeout), "cwd": params.get("cwd")})
