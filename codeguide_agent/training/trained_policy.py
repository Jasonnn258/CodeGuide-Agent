from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TrainedPatchPolicy:
    """Lightweight policy facade for future trained artifacts.

    P8 intentionally does not load model weights. This facade reads artifact
    metadata and returns deterministic patch candidates for replay/eval smoke
    tests.
    """

    name = "trained"

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.artifacts = self._load_artifacts()
        self._patches = {
            str(candidate.get("task_id", "")): str(candidate.get("final_patch", ""))
            for candidate in self.artifacts.get("patch_candidates", [])
            if str(candidate.get("final_patch", "")).startswith("diff --git")
        }

    @property
    def available_task_ids(self) -> list[str]:
        return sorted(self._patches)

    @property
    def artifact_type(self) -> str:
        return str(self.artifacts.get("artifact_type", "unknown"))

    @property
    def contains_model_weights(self) -> bool:
        return bool(self.artifacts.get("contains_model_weights", False))

    def predict_patch(self, task_id: str) -> str:
        return self._patches.get(task_id, "")

    def _load_artifacts(self) -> dict[str, Any]:
        path = self.run_dir / "artifacts.json"
        if not path.exists():
            raise FileNotFoundError(f"missing artifacts.json in {self.run_dir}")
        return json.loads(path.read_text(encoding="utf-8"))
