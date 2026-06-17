from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RolloutState:
    task_id: str
    repo_path: Path
    issue_text: str
    step_id: int
    max_steps: int
    opened_files: list[str] = field(default_factory=list)
    searched_queries: list[str] = field(default_factory=list)
    edited_files: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    invalid_action_count: int = 0
    invalid_json_count: int = 0
    unknown_tool_count: int = 0
    tool_timeout_count: int = 0
    duplicate_tool_count: int = 0
    observations: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    stop_reason: str = ""

    def action_stats(self) -> dict[str, int]:
        return {
            "invalid_json_count": self.invalid_json_count,
            "unknown_tool_count": self.unknown_tool_count,
            "timeout_count": self.tool_timeout_count,
            "duplicate_tool_calls": self.duplicate_tool_count,
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["repo_path"] = str(self.repo_path)
        return data
