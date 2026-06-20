from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    FINISH = "finish"
    GIVE_UP = "give_up"


class ObservationStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    MAX_STEPS = "max_steps"
    GAVE_UP = "gave_up"


class EventType(str, Enum):
    TASK_START = "task_start"
    ACTION = "action"
    OBSERVATION = "observation"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"


@dataclass(frozen=True)
class Task:
    description: str
    repo_path: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    issue_path: str | None = None
    public_test_cmd: str | None = None
    hidden_test_cmd: str | None = None
    max_steps: int = 8

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolCall:
    name: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Action:
    action_type: ActionType
    thought: str
    tool_call: ToolCall | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "thought": self.thought,
            "tool_call": self.tool_call.to_dict() if self.tool_call else None,
            "message": self.message,
        }


@dataclass(frozen=True)
class Observation:
    status: ObservationStatus
    output: str
    tool_name: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "output": self.output,
            "tool_name": self.tool_name,
            "error": self.error,
        }

    def is_success(self) -> bool:
        return self.status == ObservationStatus.SUCCESS


@dataclass(frozen=True)
class Event:
    event_type: EventType
    task_id: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class RunResult:
    task_id: str
    status: RunStatus
    summary: str
    steps_taken: int
    patch: str = ""
    trajectory_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "summary": self.summary,
            "steps_taken": self.steps_taken,
            "patch": self.patch,
            "trajectory_path": self.trajectory_path,
            "error": self.error,
        }
