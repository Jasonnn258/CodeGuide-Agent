from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemRole(str, Enum):
    ISSUE = "issue"
    REPO_MAP = "repo_map"
    RETRIEVED_FILE = "retrieved_file"
    TEST_SUMMARY = "test_summary"
    TOOL_TRACE = "tool_trace"
    SYSTEM = "system"
    HISTORY_RAG = "history_rag"


@dataclass
class ContextItem:
    role: ItemRole
    content: str
    token_estimate: int = 0
    meta: dict[str, Any] = field(default_factory=dict)
    dropped: bool = False
    drop_reason: str = ""


@dataclass
class ContextBudget:
    max_tokens: int = 8000
    reserved_system_tokens: int = 400
    reserved_tool_output_tokens: int = 1200

    @property
    def available(self) -> int:
        return self.max_tokens - self.reserved_system_tokens - self.reserved_tool_output_tokens


@dataclass
class ContextPack:
    items: list[ContextItem] = field(default_factory=list)
    budget: ContextBudget = field(default_factory=ContextBudget)

    @property
    def total_tokens(self) -> int:
        return sum(item.token_estimate for item in self.items if not item.dropped)

    @property
    def dropped_items(self) -> list[ContextItem]:
        return [item for item in self.items if item.dropped]

    @property
    def active_items(self) -> list[ContextItem]:
        return [item for item in self.items if not item.dropped]

    def to_prompt_text(self) -> str:
        return "\n\n".join(item.content for item in self.active_items if item.content)
