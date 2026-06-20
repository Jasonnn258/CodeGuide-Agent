from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import ast
import re
import subprocess

from codeguide_agent.rollout.actions import Action
from codeguide_agent.rollout.state import RolloutState


class BasePolicy(ABC):
    name = "base"

    @abstractmethod
    def next_action(self, state: RolloutState) -> Action | dict[str, Any] | str:
        raise NotImplementedError


class NoopPolicy(BasePolicy):
    name = "noop"

    def next_action(self, state: RolloutState) -> Action:
        return Action("Stop without editing for deterministic baseline.", "stop", {"reason": "policy_stop"})


class GoldPatchPolicy(BasePolicy):
    name = "gold"

    def next_action(self, state: RolloutState) -> Action:
        if not state.edited_files:
            return Action("Apply the task gold patch in the isolated workspace.", "apply_gold_patch", {})
        if not state.tests_run:
            return Action("Run public verifier after gold patch.", "run_test", {"command": "__PUBLIC_TEST__"})
        return Action("Stop after gold patch verification.", "stop", {"reason": "gold_policy_complete"})

    def apply_gold_patch(self, repo_path: str | Path) -> dict[str, Any]:
        repo = Path(repo_path)
        proc = subprocess.run(["git", "apply", "gold.patch"], cwd=repo, text=True, capture_output=True)
        return {
            "tool_name": "apply_gold_patch",
            "status": "success" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }


class ScriptedSearchPatchPolicy(BasePolicy):
    name = "scripted"

    def next_action(self, state: RolloutState) -> Action:
        if state.step_id == 0:
            return Action("Inspect repository layout.", "repo_tree", {"max_depth": 4})
        if not state.searched_queries:
            return Action("Search for issue keywords.", "search_repo", {"query": _issue_query(state.issue_text), "path": "src", "file_glob": "*.py"})
        if state.searched_queries and not state.opened_files:
            match_file = _first_match_file(state.observations)
            if match_file:
                return Action("Read the first matching source file.", "read_file", {"file_path": match_file})
        return Action("Stop after deterministic search/read scaffold.", "stop", {"reason": "scripted_policy_complete"})


class HeuristicLocalizePolicy(BasePolicy):
    name = "heuristic"

    def __init__(self, max_reads: int = 3) -> None:
        self.max_reads = max_reads

    def next_action(self, state: RolloutState) -> Action:
        if state.step_id == 0:
            return Action("Inspect allowed repository layout.", "repo_tree", {"max_depth": 4})
        if not state.searched_queries:
            return Action("Search source files for the strongest issue keyword.", "search_repo", {"query": _top_query(state), "path": "src", "file_glob": "*.py"})
        target = self._next_candidate(state)
        if target:
            return Action("Read the next highest-ranked source candidate.", "read_file", {"file_path": target})
        return Action("Stop after localize-only heuristic inspection.", "stop", {"reason": "heuristic_localize_complete"})

    def _next_candidate(self, state: RolloutState) -> str | None:
        for candidate in _rank_source_files(state.repo_path, state.issue_text):
            if candidate not in state.opened_files:
                return candidate
            if len(state.opened_files) >= self.max_reads:
                return None
        return None


def _issue_query(issue_text: str) -> str:
    tokens = re.findall(r"[A-Za-z_]{4,}", issue_text.lower())
    stop = {"should", "with", "from", "this", "that", "currently", "when", "file", "files"}
    useful = [token for token in tokens if token not in stop]
    return useful[0] if useful else "def"


def _top_query(state: RolloutState) -> str:
    tokens = _issue_tokens(state.issue_text)
    return tokens[0] if tokens else "def"


def _issue_tokens(issue_text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", issue_text.lower())
    stop = {
        "the", "and", "for", "with", "from", "this", "that", "are", "but", "can",
        "should", "currently", "when", "where", "file", "files", "value", "values",
        "running", "accepted", "output", "remain", "remains", "through",
    }
    important = {"config", "yaml", "path", "cache", "csv", "cli", "parse", "parser", "amount", "discount", "region", "uppercase", "formatter", "calculator"}
    scored: dict[str, int] = {}
    for token in tokens:
        if token in stop:
            continue
        scored[token] = scored.get(token, 0) + (3 if token in important else 1)
    return [token for token, _ in sorted(scored.items(), key=lambda item: (-item[1], item[0]))]


def _rank_source_files(repo_path: str | Path, issue_text: str) -> list[str]:
    root = Path(repo_path)
    tokens = _issue_tokens(issue_text)
    scored: list[tuple[int, str]] = []
    for path in sorted((root / "src").rglob("*.py")):
        relative = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        haystacks = {
            "path": str(relative).lower().replace("_", " "),
            "name": path.stem.lower().replace("_", " "),
            "content": text.lower().replace("_", " "),
            "symbols": " ".join(_python_symbols(text)).lower().replace("_", " "),
        }
        score = 0
        for token in tokens:
            score += 5 * haystacks["name"].count(token)
            score += 4 * haystacks["path"].count(token)
            score += 3 * haystacks["symbols"].count(token)
            score += haystacks["content"].count(token)
        if score:
            scored.append((score, str(relative)))
    return [relative for _, relative in sorted(scored, key=lambda item: (-item[0], item[1]))]


def _python_symbols(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
    return symbols


def _first_match_file(observations: list[dict[str, Any]]) -> str | None:
    for row in reversed(observations):
        observation = row.get("observation", {})
        matches = observation.get("matches", [])
        if matches:
            return matches[0].get("file")
    return None


def make_policy(name: str) -> BasePolicy:
    if name == "noop":
        return NoopPolicy()
    if name == "scripted":
        return ScriptedSearchPatchPolicy()
    if name in {"heuristic", "localize_only"}:
        return HeuristicLocalizePolicy()
    if name == "llm":
        from codeguide_agent.rollout.llm_policy import LLMPolicy

        return LLMPolicy()
    if name == "gold":
        return GoldPatchPolicy()
    raise ValueError(f"unknown policy: {name}")
