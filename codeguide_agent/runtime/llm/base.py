from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from codeguide_agent.runtime.agent.types import Action, ActionType


@dataclass(frozen=True)
class LLMResponse:
    action: Action
    raw_content: str = ""
    total_tokens: int = 0


class LLMBackend(Protocol):
    def next_action(self, messages: list[dict[str, str]]) -> LLMResponse:
        ...


class MockBackend:
    """Deterministic fallback backend used when no LLM key is configured."""

    def next_action(self, messages: list[dict[str, str]]) -> LLMResponse:
        return LLMResponse(
            action=Action(ActionType.FINISH, thought="Mock backend does not call external APIs.", message="mock complete"),
            raw_content="mock complete",
            total_tokens=0,
        )
