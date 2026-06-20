from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from codeguide_agent.runtime.agent.types import Action, Event, EventType, Observation, Task


class EventLog:
    """Append-only JSONL event log for runtime trajectories."""

    def __init__(self, path: str | Path, task_id: str) -> None:
        self.path = Path(path)
        self.task_id = task_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def append(self, event_type: EventType, payload: dict[str, Any]) -> None:
        event = Event(event_type=event_type, task_id=self.task_id, payload=payload)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    def task_start(self, task: Task) -> None:
        self.append(EventType.TASK_START, {"task": task.to_dict()})

    def action(self, step: int, action: Action) -> None:
        self.append(EventType.ACTION, {"step": step, "action": action.to_dict()})

    def observation(self, step: int, observation: Observation) -> None:
        self.append(EventType.OBSERVATION, {"step": step, "observation": observation.to_dict()})

    def complete(self, steps: int, summary: str) -> None:
        self.append(EventType.TASK_COMPLETE, {"steps": steps, "summary": summary})

    def failed(self, steps: int, reason: str) -> None:
        self.append(EventType.TASK_FAILED, {"steps": steps, "reason": reason})
