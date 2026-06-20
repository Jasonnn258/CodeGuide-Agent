from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from codeguide_agent.reward.hacking_checks import changed_files_from_diff


def gold_file_patched(diff_text: str, gold_files: list[str]) -> bool:
    changed = set(changed_files_from_diff(diff_text))
    return bool(changed.intersection(gold_files))


def gold_function_patched(diff_text: str, repo_path: str | Path, gold_functions: list[str], gold_files: list[str] | None = None) -> bool:
    if not gold_functions:
        return False
    changed = set(changed_files_from_diff(diff_text))
    candidates = sorted(changed.intersection(gold_files or changed) or changed)
    return _any_file_defines_function(repo_path, candidates, gold_functions)


def gold_file_hit(diff_text: str, gold_files: list[str]) -> bool:
    return gold_file_patched(diff_text, gold_files)


def gold_function_hit(diff_text: str, repo_path: str | Path, gold_functions: list[str], gold_files: list[str] | None = None) -> bool:
    return gold_function_patched(diff_text, repo_path, gold_functions, gold_files)


def patch_localization_metrics(
    diff_text: str,
    repo_path: str | Path,
    gold_files: list[str],
    gold_functions: list[str],
) -> dict[str, bool]:
    return {
        "gold_file_patched": gold_file_patched(diff_text, gold_files),
        "gold_function_patched": gold_function_patched(diff_text, repo_path, gold_functions, gold_files),
    }


def localization_process_metrics(
    trajectory_rows: list[dict[str, Any]],
    repo_path: str | Path,
    gold_files: list[str],
    gold_functions: list[str],
) -> dict[str, bool]:
    candidates = _explored_files(trajectory_rows)
    first_3 = candidates[:3]
    first_5 = candidates[:5]
    return {
        "gold_file_hit_at_3": _gold_file_in_candidates(first_3, gold_files),
        "gold_file_hit_at_5": _gold_file_in_candidates(first_5, gold_files),
        "gold_function_hit_at_3": _any_file_defines_function(repo_path, first_3, gold_functions),
        "gold_function_hit_at_5": _any_file_defines_function(repo_path, first_5, gold_functions),
        "localization_candidates": candidates,
    }


def _explored_files(rows: list[dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for row in rows:
        action_name = row.get("action_name")
        action_input = row.get("action_input", {})
        observation = row.get("observation", {})
        if action_name == "read_file" and action_input.get("file_path"):
            _append_unique(candidates, str(action_input["file_path"]))
        if action_name == "search_repo":
            for match in observation.get("matches", []):
                file_name = match.get("file")
                if file_name:
                    _append_unique(candidates, str(file_name))
    return candidates


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _gold_file_in_candidates(candidates: list[str], gold_files: list[str]) -> bool:
    return bool(set(candidates).intersection(gold_files))


def _any_file_defines_function(repo_path: str | Path, candidates: list[str], gold_functions: list[str]) -> bool:
    if not gold_functions:
        return False
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
