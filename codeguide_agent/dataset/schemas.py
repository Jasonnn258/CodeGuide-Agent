from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


REQUIRED_METADATA_FIELDS = {
    "task_id",
    "scenario",
    "bug_type",
    "difficulty",
    "repo_path",
    "issue_path",
    "gold_files",
    "gold_functions",
    "gold_patch",
    "public_test_cmd",
    "hidden_test_cmd",
    "forbidden_behaviors",
    "source",
    "split",
}


@dataclass(frozen=True)
class MiniRepoTask:
    task_id: str
    scenario: str
    bug_type: str
    difficulty: str
    repo_path: str
    issue_path: str
    gold_files: list[str]
    gold_functions: list[str]
    gold_patch: str
    public_test_cmd: str
    hidden_test_cmd: str
    forbidden_behaviors: list[str]
    source: str
    split: str

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "MiniRepoTask":
        missing = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
        if missing:
            raise ValueError(f"missing metadata fields: {', '.join(missing)}")
        return cls(
            task_id=str(metadata["task_id"]),
            scenario=str(metadata["scenario"]),
            bug_type=str(metadata["bug_type"]),
            difficulty=str(metadata["difficulty"]),
            repo_path=str(metadata["repo_path"]),
            issue_path=str(metadata["issue_path"]),
            gold_files=list(metadata["gold_files"]),
            gold_functions=list(metadata["gold_functions"]),
            gold_patch=str(metadata["gold_patch"]),
            public_test_cmd=str(metadata["public_test_cmd"]),
            hidden_test_cmd=str(metadata["hidden_test_cmd"]),
            forbidden_behaviors=list(metadata["forbidden_behaviors"]),
            source=str(metadata["source"]),
            split=str(metadata["split"]),
        )


def load_metadata(task_dir: str | Path) -> dict[str, Any]:
    metadata_path = Path(task_dir) / "metadata.json"
    with metadata_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_task(task_dir: str | Path) -> MiniRepoTask:
    return MiniRepoTask.from_metadata(load_metadata(task_dir))
