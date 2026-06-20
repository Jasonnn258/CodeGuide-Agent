from __future__ import annotations

from pathlib import Path


class RepoMap:
    def __init__(self, repo_path: str | Path, max_files: int = 200) -> None:
        self.repo_path = Path(repo_path)
        self.max_files = max_files

    def build(self) -> str:
        lines: list[str] = []
        ignored = {".git", "__pycache__", ".pytest_cache"}
        for path in sorted(self.repo_path.rglob("*")):
            rel = path.relative_to(self.repo_path)
            if any(part in ignored for part in rel.parts):
                continue
            if path.is_file():
                lines.append(str(rel))
                if len(lines) >= self.max_files:
                    lines.append("...[truncated]...")
                    break
        return "\n".join(lines)
