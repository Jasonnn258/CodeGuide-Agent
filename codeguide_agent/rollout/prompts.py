from __future__ import annotations

import json
from typing import Any


FORBIDDEN_PROMPT_TERMS = ("metadata.json", "gold.patch", "tests_hidden")


def build_llm_prompt(
    issue_text: str,
    public_test_cmd: str,
    observations: list[dict[str, Any]],
    opened_files: list[str],
    searched_queries: list[str],
) -> str:
    allowed_observations = [_safe_observation(row) for row in observations[-8:]]
    allowed_observations = [row for row in allowed_observations if row]
    prompt = "\n".join(
        [
            "You are a repo debugging agent.",
            "First localize the likely bug before patching.",
            "Prefer minimal source-code patches.",
            "Use public tests only.",
            "Never access evaluator-only files.",
            "Emit exactly one JSON action and no prose outside JSON.",
            "Read a file before editing it.",
            "After a successful edit, run public tests, read the edited file, or inspect git_diff before another edit.",
            "If edit_file fails, read the current file before retrying.",
            "Do not repeat the same file_path and old_text edit.",
            "Use git_diff to inspect the final patch.",
            "Stop only after public test plus git_diff, or if blocked/uncertain.",
            "Never expose metadata.json, gold.patch, tests_hidden, hidden commands, or hidden logs.",
            "Always use repo-relative file paths like src/pricing.py.",
            "Never use absolute temp paths such as /private/tmp/... in file_path.",
            "",
            "Allowed actions use this shape:",
            '{"action":"repo_tree","args":{"max_depth":4}}',
            '{"action":"search_repo","args":{"query":"parser","path":"src","file_glob":"*.py"}}',
            '{"action":"read_file","args":{"file_path":"src/example.py"}}',
            '{"action":"edit_file","args":{"file_path":"src/example.py","old_text":"old","new_text":"new"}}',
            '{"action":"run_test","args":{"command":"__PUBLIC_TEST__"}}',
            '{"action":"git_diff","args":{}}',
            '{"action":"stop","args":{"reason":"done_or_uncertain"}}',
            "",
            "Issue:",
            issue_text.strip(),
            "",
            "Public test command:",
            public_test_cmd,
            "",
            "Opened files:",
            json.dumps(opened_files[-5:], sort_keys=True),
            "",
            "Searched queries:",
            json.dumps(searched_queries[-5:], sort_keys=True),
            "",
            "Recent allowed observations:",
            json.dumps(allowed_observations, sort_keys=True),
        ]
    )
    return _redact_forbidden(prompt)


def _safe_observation(row: dict[str, Any]) -> dict[str, Any]:
    action_name = row.get("action_name", "")
    if action_name not in {"repo_tree", "search_repo", "read_file", "run_test", "git_diff", "invalid_action"}:
        return {}
    action_input = _filter_payload(row.get("action_input", {}))
    observation = _filter_payload(row.get("observation", {}))
    if action_name == "run_test" and _is_hidden_test_payload(action_input):
        return {}
    return {
        "action_name": action_name,
        "action_input": action_input,
        "observation": observation,
    }


def _filter_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _filter_payload(value) for key, value in payload.items() if _allowed_text(str(key))}
    if isinstance(payload, list):
        return [_filter_payload(value) for value in payload if _allowed_text(str(value))]
    if isinstance(payload, str):
        return payload if _allowed_text(payload) else "<redacted>"
    return payload


def _allowed_text(text: str) -> bool:
    lowered = text.lower()
    return not any(term in lowered for term in FORBIDDEN_PROMPT_TERMS)


def _is_hidden_test_payload(action_input: dict[str, Any]) -> bool:
    phase = str(action_input.get("phase", "")).lower()
    command = str(action_input.get("command", "")).lower()
    return "hidden" in phase or "tests_hidden" in command


def _redact_forbidden(text: str) -> str:
    redacted = text
    for term in FORBIDDEN_PROMPT_TERMS:
        redacted = redacted.replace(term, "<redacted>")
    return redacted
