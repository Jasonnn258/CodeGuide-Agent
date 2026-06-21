from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from codeguide_agent.trajectory.schemas import TrajectoryStep


class TrajectoryLogger:
    def __init__(self, path: str | Path, task_id: str, trajectory_id: str, model: str = "deterministic_baseline", model_config: dict[str, Any] | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.trajectory_id = trajectory_id
        self.model = model
        self.model_config = model_config or {}
        self.step_count = 0

    def log_step(
        self,
        action_name: str,
        action_input: dict[str, Any],
        observation: dict[str, Any],
        thought: str = "",
    ) -> dict[str, Any]:
        self.step_count += 1
        step = TrajectoryStep(self.step_count, action_name, action_input, observation, thought)
        row = {
            "type": "step",
            "task_id": self.task_id,
            "trajectory_id": self.trajectory_id,
            "model": self.model,
            "model_config": self.model_config,
            **step.to_dict(),
        }
        self._append(row)
        return row

    def log_final(self, final_patch: str, reward: dict[str, Any], final_status: str) -> dict[str, Any]:
        row = {
            "type": "final",
            "task_id": self.task_id,
            "trajectory_id": self.trajectory_id,
            "model": self.model,
            "model_config": self.model_config,
            "final_patch": final_patch,
            "reward": reward,
            "final_status": final_status,
            "tool_calls": self.step_count,
        }
        self._append(row)
        return row

    def _append(self, row: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
