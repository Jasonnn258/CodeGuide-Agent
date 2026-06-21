import json
from pathlib import Path

from codeguide_agent.eval.run_eval import discover_tasks


def test_discover_tasks_merges_manifest_and_repo_dirs(tmp_path: Path):
    root = tmp_path / "mini"
    repos = root / "repos"
    (repos / "task_001").mkdir(parents=True)
    (repos / "task_021").mkdir(parents=True)
    (root / "tasks.jsonl").write_text(
        json.dumps({"task_id": "task_001", "repo_path": str(repos / "task_001")}) + "\n",
        encoding="utf-8",
    )

    tasks = discover_tasks(root)

    assert [path.name for path in tasks] == ["task_001", "task_021"]
    assert [path.name for path in discover_tasks(root, task_id="task_021")] == ["task_021"]
