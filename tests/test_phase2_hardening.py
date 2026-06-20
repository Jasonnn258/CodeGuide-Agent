import json
import shutil
import subprocess
from pathlib import Path

from codeguide_agent.baselines.prompt_only import run_baseline
from codeguide_agent.eval.run_eval import compute_repo_checksum
from codeguide_agent.eval_mini_repo import evaluate_one
from codeguide_agent.datasets.mini_repo_debug import load_tasks
from codeguide_agent.training_data.build_sft_from_trajectories import build_sft_dataset


def _copy_task_with_git(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
    subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.local", "-c", "user.name=Test", "commit", "-qm", "initial"],
        cwd=destination,
        check=True,
    )
    return destination


def test_prompt_only_noop_navigation_does_not_leak_gold_metadata(tmp_path: Path):
    task = _copy_task_with_git(Path("data/mini_repo_debug/repos/task_001"), tmp_path / "task_001")

    result = run_baseline(task, mode="noop", trajectories_dir=tmp_path / "trajectories", run_hidden=False)

    rows = [json.loads(line) for line in Path(result["trajectory"]).read_text(encoding="utf-8").splitlines()]
    metadata = json.loads((task / "metadata.json").read_text(encoding="utf-8"))
    forbidden = set(metadata["gold_files"]) | set(metadata["gold_functions"])
    for row in rows:
        if row.get("type") != "step":
            continue
        visible = json.dumps(
            {"action_input": row.get("action_input", {}), "observation": row.get("observation", {})},
            sort_keys=True,
        )
        assert not any(token in visible for token in forbidden)


def test_sft_builder_excludes_gold_policy_apply_gold_patch(tmp_path: Path):
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir()
    (trajectories / "task_001_gold.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "step",
                        "task_id": "task_001",
                        "trajectory_id": "task_001_gold",
                        "thought": "cheat",
                        "action_name": "apply_gold_patch",
                        "action_input": {},
                        "observation": {"status": "success"},
                    }
                ),
                json.dumps(
                    {
                        "type": "final",
                        "task_id": "task_001",
                        "trajectory_id": "task_001_gold",
                        "final_status": "success",
                        "reward": {"public_pass": True, "hidden_pass": True},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (trajectories / "task_001_scripted.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "step",
                        "task_id": "task_001",
                        "trajectory_id": "task_001_scripted",
                        "thought": "inspect",
                        "action_name": "repo_tree",
                        "action_input": {},
                        "observation": {"status": "success"},
                    }
                ),
                json.dumps(
                    {
                        "type": "final",
                        "task_id": "task_001",
                        "trajectory_id": "task_001_scripted",
                        "final_status": "success",
                        "reward": {"public_pass": True, "hidden_pass": True},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "sft.jsonl"

    result = build_sft_dataset(trajectories, output)

    assert result["samples_written"] == 1
    text = output.read_text(encoding="utf-8")
    assert "task_001_scripted" in text
    assert "task_001_gold" not in text
    assert "apply_gold_patch" not in text


def test_eval_mini_repo_reports_original_checksum_safety(tmp_path: Path):
    task = load_tasks("data/mini_repo_debug/tasks.jsonl", task_id="task_001")[0]
    before = compute_repo_checksum(task.repo_path)

    result = evaluate_one(
        task,
        trajectory_dir=tmp_path / "trajectories",
        workspace_root=tmp_path / "workspaces",
        timeout=30,
    )

    assert result["original_repo_unchanged"] is True
    assert result["original_checksum_before"] == before
    assert result["original_checksum_after"] == before
    assert compute_repo_checksum(task.repo_path) == before
