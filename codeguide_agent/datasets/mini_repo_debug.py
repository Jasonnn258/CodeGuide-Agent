from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codeguide_agent.dataset.schemas import load_metadata


@dataclass(frozen=True)
class MiniRepoDebugTask:
    task_id: str
    repo_path: Path
    issue_path: Path
    metadata: dict[str, Any]

    @property
    def description(self) -> str:
        if self.issue_path.exists():
            return self.issue_path.read_text(encoding="utf-8").strip()
        return self.metadata.get("scenario", "Mini-Repo-Debug repair task")


def load_tasks(tasks_jsonl: str | Path, task_id: str | None = None) -> list[MiniRepoDebugTask]:
    path = Path(tasks_jsonl)
    base = path.parent.parent.parent if path.parts[-3:] == ("data", "mini_repo_debug", "tasks.jsonl") else Path.cwd()
    tasks: list[MiniRepoDebugTask] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if task_id and row.get("task_id") != task_id:
            continue
        repo_path = Path(row["repo_path"])
        if not repo_path.is_absolute():
            repo_path = (Path.cwd() / repo_path).resolve()
        metadata = load_metadata(repo_path)
        issue_path = repo_path / metadata.get("issue_path", "issue.md")
        tasks.append(MiniRepoDebugTask(task_id=metadata["task_id"], repo_path=repo_path, issue_path=issue_path, metadata=metadata))
    return tasks
