from __future__ import annotations

from pathlib import Path
from typing import Any

from codeguide_agent.runtime.tools.base import BaseTool, ToolResult


MAX_FILE_CHARS = 20_000


def resolve_in_repo(repo_path: str | Path, relative_path: str) -> Path:
    root = Path(repo_path).resolve()
    target = (root / relative_path).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"path escapes repo: {relative_path}")
    return target


class FileReadTool(BaseTool):
    name = "file_read"

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path)

    def execute(self, params: dict[str, Any]) -> ToolResult:
        path = resolve_in_repo(self.repo_path, str(params.get("path", "")))
        if not path.is_file():
            return ToolResult(False, "", f"file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n...[truncated]...\n"
        return ToolResult(True, text)


class FileWriteTool(BaseTool):
    name = "file_write"

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path)

    def execute(self, params: dict[str, Any]) -> ToolResult:
        path = resolve_in_repo(self.repo_path, str(params.get("path", "")))
        text = str(params.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return ToolResult(True, f"wrote {path.relative_to(self.repo_path.resolve())}")
