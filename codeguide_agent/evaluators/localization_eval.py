from __future__ import annotations

import ast
from pathlib import Path

from codeguide_agent.reward.hacking_checks import changed_files_from_diff


def gold_file_hit(diff_text: str, gold_files: list[str]) -> bool:
    changed = set(changed_files_from_diff(diff_text))
    return bool(changed.intersection(gold_files))


def gold_function_hit(diff_text: str, repo_path: str | Path, gold_functions: list[str], gold_files: list[str] | None = None) -> bool:
    if not gold_functions:
        return False
    changed = set(changed_files_from_diff(diff_text))
    candidates = sorted(changed.intersection(gold_files or changed) or changed)
    for relative in candidates:
        path = Path(repo_path) / relative
        if not path.exists() or path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if defined.intersection(gold_functions):
            return True
    return False
