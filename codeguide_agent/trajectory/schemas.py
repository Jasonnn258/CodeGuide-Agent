from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    step_id: int
    action_name: str
    action_input: dict[str, Any]
    observation: dict[str, Any]
    thought: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryRecord:
    trajectory_id: str
    task_id: str
    model: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_patch: str = ""
    reward: dict[str, Any] = field(default_factory=dict)
    final_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data
