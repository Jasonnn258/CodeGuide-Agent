from __future__ import annotations

import json
import time
from typing import Any

from codeguide_agent.rollout.actions import Action, SUPPORTED_ACTIONS
from codeguide_agent.rollout.llm_client import LLMClient, make_llm_client
from codeguide_agent.rollout.llm_config import LLMConfig
from codeguide_agent.rollout.policy import BasePolicy
from codeguide_agent.rollout.prompts import build_llm_prompt
from codeguide_agent.rollout.state import RolloutState


FORBIDDEN_ACTION_TERMS = ("metadata.json", "gold.patch", "tests_hidden")


class LLMPolicy(BasePolicy):
    name = "llm"

    def __init__(self, config: LLMConfig | None = None, client: LLMClient | None = None) -> None:
        self.config = config or LLMConfig.from_env()
        self.client = client or make_llm_client(self.config)
        self.llm_calls = 0
        self.total_tokens = 0
        self.last_skip_reason = self.config.skip_reason
        self.last_availability = self.config.availability_label
        self.last_prompt_preview = ""
        self.last_response_preview = ""
        self.last_error = ""
        self._last_call_time = 0.0

    def next_action(self, state: RolloutState) -> Action | dict[str, Any] | str:
        if not self.config.available:
            return Action(
                f"LLM backend unavailable: {self.config.skip_reason}",
                "stop",
                {"reason": "llm_skipped", "skip_reason": self.config.skip_reason},
            )
        if self.llm_calls >= self.config.max_calls_per_task:
            return Action("Stop after hitting LLM call cap.", "stop", {"reason": "llm_call_cap"})

        for attempt in range(2):
            prompt = build_llm_prompt(
                issue_text=state.issue_text,
                public_test_cmd="__PUBLIC_TEST__",
                observations=state.observations,
                opened_files=state.opened_files,
                searched_queries=state.searched_queries,
            )
            self.last_prompt_preview = prompt[:1000]
            self._respect_qps_limit()
            result = self.client.complete(prompt)
            self.llm_calls += 1
            self.total_tokens += int(result.total_tokens or 0)
            self.last_response_preview = result.content[:1000]
            if result.status != "success":
                self.last_error = result.error
                return Action("Stop after LLM backend error.", "stop", {"reason": "llm_backend_error", "error": result.error[:200]})
            parsed = self._parse_model_action(result.content)
            if parsed["ok"]:
                return parsed["action"]
            self.last_error = parsed["error"]
            if attempt == 0 and self.llm_calls < self.config.max_calls_per_task:
                continue
            return result.content
        return Action("Stop after invalid LLM responses.", "stop", {"reason": "llm_invalid_response"})

    def metadata(self) -> dict[str, Any]:
        return {
            "availability": self.last_availability,
            "skip_reason": self.last_skip_reason,
            "llm_calls": self.llm_calls,
            "llm_total_tokens": self.total_tokens,
            "llm_config": self.config.safe_dict(),
            "last_prompt_preview": self.last_prompt_preview,
            "last_response_preview": self.last_response_preview,
            "last_error": self.last_error,
        }

    def _parse_model_action(self, content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"invalid json: {exc}"}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "model action must be a JSON object"}
        action_name = payload.get("action", payload.get("action_name"))
        args = payload.get("args", payload.get("action_input", {}))
        if not isinstance(action_name, str) or action_name not in SUPPORTED_ACTIONS or action_name == "apply_gold_patch":
            return {"ok": False, "error": f"unknown or disallowed action: {action_name}"}
        if not isinstance(args, dict):
            return {"ok": False, "error": "action args must be an object"}
        if _contains_forbidden(args) or _hidden_test_command(args):
            return {
                "ok": True,
                "action": Action(
                    f"Reject LLM request for evaluator-only or hidden-test access. response_preview={self.last_response_preview[:200]!r}",
                    "stop",
                    {"reason": "llm_forbidden_action_rejected"},
                ),
            }
        return {
            "ok": True,
            "action": Action(
                (
                    f"LLM action via {self.config.availability_label} backend. "
                    f"prompt_preview={self.last_prompt_preview[:200]!r} "
                    f"response_preview={self.last_response_preview[:200]!r}"
                ),
                action_name,
                _normalize_args(action_name, args),
            ),
        }

    def _respect_qps_limit(self) -> None:
        if self.config.mock or self.config.backend == "mock":
            return
        if self.config.qps_limit <= 0:
            return
        interval = 1.0 / self.config.qps_limit
        elapsed = time.monotonic() - self._last_call_time
        if self._last_call_time and elapsed < interval:
            time.sleep(interval - elapsed)
        self._last_call_time = time.monotonic()


def _normalize_args(action_name: str, args: dict[str, Any]) -> dict[str, Any]:
    if action_name == "run_test" and args.get("command") in {"public", "pytest"}:
        return {**args, "command": "__PUBLIC_TEST__"}
    return args


def _contains_forbidden(payload: Any) -> bool:
    text = json.dumps(payload, sort_keys=True).lower()
    return any(term in text for term in FORBIDDEN_ACTION_TERMS)


def _hidden_test_command(args: dict[str, Any]) -> bool:
    command = str(args.get("command", "")).lower()
    return "hidden" in command or "tests_hidden" in command
