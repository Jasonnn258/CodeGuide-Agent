from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import json


SUPPORTED_ACTIONS = {
    "repo_tree",
    "search_repo",
    "read_file",
    "edit_file",
    "run_test",
    "git_diff",
    "rollback",
    "stop",
    "apply_gold_patch",
}


@dataclass(frozen=True)
class Action:
    thought: str
    action_name: str
    action_input: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionParseResult:
    ok: bool
    action: Action | None = None
    error: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.action is not None:
            data["action"] = self.action.to_dict()
        return data


def parse_action(raw: str | dict[str, Any]) -> ActionParseResult:
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return ActionParseResult(False, error=f"invalid json: {exc}", error_type="invalid_json")
    elif isinstance(raw, dict):
        payload = raw
    else:
        return ActionParseResult(False, error="action must be a dict or JSON string", error_type="invalid_json")

    if not isinstance(payload, dict):
        return ActionParseResult(False, error="action payload must be an object", error_type="invalid_json")

    action_name = payload.get("action_name")
    if not isinstance(action_name, str) or not action_name:
        return ActionParseResult(False, error="missing action_name", error_type="missing_args")
    if action_name not in SUPPORTED_ACTIONS:
        return ActionParseResult(False, error=f"unknown tool: {action_name}", error_type="unknown_tool")

    action_input = payload.get("action_input", {})
    if not isinstance(action_input, dict):
        return ActionParseResult(False, error="action_input must be an object", error_type="missing_args")

    thought = payload.get("thought", "")
    if not isinstance(thought, str):
        return ActionParseResult(False, error="thought must be a string", error_type="missing_args")

    missing = _missing_required_args(action_name, action_input)
    if missing:
        return ActionParseResult(False, error=f"missing args for {action_name}: {', '.join(missing)}", error_type="missing_args")

    return ActionParseResult(True, action=Action(thought=thought, action_name=action_name, action_input=action_input))


def _missing_required_args(action_name: str, action_input: dict[str, Any]) -> list[str]:
    required: dict[str, list[str]] = {
        "search_repo": ["query"],
        "read_file": ["file_path"],
        "edit_file": ["file_path", "old_text", "new_text"],
        "run_test": ["command"],
    }
    return [name for name in required.get(action_name, []) if name not in action_input]
