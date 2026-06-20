from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
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


def _issue_query(issue_text: str) -> str:
    tokens = re.findall(r"[A-Za-z_]{4,}", issue_text.lower())
    stop = {"should", "with", "from", "this", "that", "currently", "when", "file", "files"}
    useful = [token for token in tokens if token not in stop]
    return useful[0] if useful else "def"


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
    if name == "gold":
        return GoldPatchPolicy()
    raise ValueError(f"unknown policy: {name}")
