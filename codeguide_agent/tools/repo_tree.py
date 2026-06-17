from __future__ import annotations

from pathlib import Path

from codeguide_agent.tools.common import CHECKPOINT_DIR, resolve_repo_path


def repo_tree(repo_path: str | Path, max_depth: int = 4) -> dict:
    root = resolve_repo_path(repo_path)
    entries: list[str] = []
    ignored = {".git", "__pycache__", ".pytest_cache", CHECKPOINT_DIR}

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        if len(relative.parts) > max_depth:
            continue
        suffix = "/" if path.is_dir() else ""
        entries.append(f"{relative}{suffix}")

    return {"tool_name": "repo_tree", "status": "success", "root": str(root), "entries": entries}
