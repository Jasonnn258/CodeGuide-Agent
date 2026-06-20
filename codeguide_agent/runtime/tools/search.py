from __future__ import annotations

from pathlib import Path
from typing import Any

from codeguide_agent.runtime.tools.base import BaseTool, ToolResult


class SearchTool(BaseTool):
    name = "search"

    def __init__(self, repo_path: str | Path, max_matches: int = 80) -> None:
        self.repo_path = Path(repo_path)
        self.max_matches = max_matches

    def execute(self, params: dict[str, Any]) -> ToolResult:
        needle = str(params.get("query", ""))
        if not needle:
            return ToolResult(False, "", "query is required")
        matches: list[str] = []
        for path in sorted(self.repo_path.rglob("*.py")):
            if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
                continue
            rel = path.relative_to(self.repo_path)
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if needle in line:
                    matches.append(f"{rel}:{line_no}:{line.strip()}")
                    if len(matches) >= self.max_matches:
                        return ToolResult(True, "\n".join(matches))
        return ToolResult(True, "\n".join(matches))
