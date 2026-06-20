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
    repeated_edit_count: int = 0
    edit_retry_count: int = 0
    syntax_error: bool = False
    syntax_error_files: list[str] = field(default_factory=list)
    incomplete_stop: bool = False
    final_test_ran: bool = False
    final_diff_collected: bool = False
    _seen_edit_keys: set[tuple[str, str]] = field(default_factory=set, repr=False)
    _last_edit_status: str = ""
    _last_edit_file: str = ""
    _requires_post_edit_check: bool = False
    _requires_read_after_failed_edit: bool = False
    observations: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    stop_reason: str = ""

    def action_stats(self) -> dict[str, int]:
        return {
            "invalid_json_count": self.invalid_json_count,
            "unknown_tool_count": self.unknown_tool_count,
            "timeout_count": self.tool_timeout_count,
            "duplicate_tool_calls": self.duplicate_tool_count,
            "repeated_edit_count": self.repeated_edit_count,
            "edit_retry_count": self.edit_retry_count,
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["repo_path"] = str(self.repo_path)
        return data
