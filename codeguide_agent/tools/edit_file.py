from __future__ import annotations

from pathlib import Path

from codeguide_agent.tools.common import create_checkpoint, resolve_repo_path


def edit_file(
    repo_path: str | Path,
    file_path: str | Path,
    old_text: str,
    new_text: str,
    expected_replacements: int = 1,
) -> dict:
    try:
        target = resolve_repo_path(repo_path, file_path)
        content = target.read_text(encoding="utf-8")
        replacements = content.count(old_text)
        if replacements != expected_replacements:
            return {
                "tool_name": "edit_file",
                "status": "error",
                "file": str(file_path),
                "error": f"expected {expected_replacements} replacement(s), found {replacements}",
            }
        checkpoint = create_checkpoint(repo_path, file_path)
        target.write_text(content.replace(old_text, new_text, expected_replacements), encoding="utf-8")
        return {
            "tool_name": "edit_file",
            "status": "success",
            "file": str(file_path),
            "replacements": replacements,
            **checkpoint,
        }
    except Exception as exc:
        return {"tool_name": "edit_file", "status": "error", "file": str(file_path), "error": str(exc)}
