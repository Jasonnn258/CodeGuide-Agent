from __future__ import annotations

from pathlib import Path

from codeguide_agent.tools.common import resolve_repo_path


def read_file(
    repo_path: str | Path,
    file_path: str | Path,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict:
    try:
        target = resolve_repo_path(repo_path, file_path)
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        start = 1 if start_line is None else max(1, start_line)
        end = len(lines) if end_line is None else min(len(lines), end_line)
        if start > end + 1:
            content = ""
        else:
            content = "".join(lines[start - 1 : end])
        return {
            "tool_name": "read_file",
            "status": "success",
            "file": str(file_path),
            "start_line": start,
            "end_line": end,
            "content": content,
        }
    except Exception as exc:
        return {"tool_name": "read_file", "status": "error", "file": str(file_path), "error": str(exc)}
