from __future__ import annotations

from pathlib import Path
import fnmatch
import shutil
import subprocess

from codeguide_agent.tools.common import CHECKPOINT_DIR, resolve_repo_path


IGNORED_PARTS = {CHECKPOINT_DIR, ".git", "__pycache__", ".pytest_cache", "tests_hidden"}
IGNORED_FILES = {"metadata.json", "gold.patch"}


def _rg_search(root: Path, query: str, path: str, file_glob: str | None, max_matches: int) -> list[dict]:
    command = ["rg", "--line-number", "--no-heading", query, path]
    if file_glob:
        command[1:1] = ["--glob", file_glob]
    proc = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=20)
    matches = []
    for line in proc.stdout.splitlines():
        pieces = line.split(":", 2)
        if len(pieces) != 3:
            continue
        file_name, line_no, text = pieces
        file_name = file_name.removeprefix("./")
        if _ignored_path(file_name):
            continue
        matches.append({"file": file_name, "line": int(line_no), "text": text})
        if len(matches) >= max_matches:
            break
    return matches


def _python_search(root: Path, query: str, path: str, file_glob: str | None, max_matches: int) -> list[dict]:
    base = resolve_repo_path(root, path)
    files = [base] if base.is_file() else sorted(base.rglob("*"))
    matches = []
    for file_path in files:
        relative = file_path.relative_to(root)
        if _ignored_path(str(relative)) or not file_path.is_file():
            continue
        if file_glob and not fnmatch.fnmatch(str(relative), file_glob):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, text in enumerate(lines, start=1):
            if query in text:
                matches.append({"file": str(relative), "line": index, "text": text})
                if len(matches) >= max_matches:
                    return matches
    return matches


def search_repo(
    repo_path: str | Path,
    query: str,
    path: str = ".",
    file_glob: str | None = None,
    max_matches: int = 50,
) -> dict:
    root = resolve_repo_path(repo_path)
    try:
        if shutil.which("rg"):
            matches = _rg_search(root, query, path, file_glob, max_matches)
            engine = "rg"
        else:
            matches = _python_search(root, query, path, file_glob, max_matches)
            engine = "python"
        return {"tool_name": "search_repo", "status": "success", "engine": engine, "matches": matches}
    except Exception as exc:
        return {"tool_name": "search_repo", "status": "error", "error": str(exc), "matches": []}


def _ignored_path(path: str) -> bool:
    relative = Path(path)
    return any(part in IGNORED_PARTS for part in relative.parts) or relative.name in IGNORED_FILES
