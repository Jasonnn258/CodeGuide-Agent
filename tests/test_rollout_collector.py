import json
from pathlib import Path

from codeguide_agent.eval.run_eval import compute_repo_checksum
from codeguide_agent.rollout.actions import parse_action
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import BasePolicy, NoopPolicy, ScriptedSearchPatchPolicy


class InvalidJsonPolicy(BasePolicy):
    name = "invalid_json"

    def next_action(self, state):
        return "{not valid json"


def test_invalid_json_action_is_rejected():
    result = parse_action("{not valid json")

    assert result.ok is False
    assert result.action is None
    assert "invalid json" in result.error


def test_unknown_tool_is_rejected():
    result = parse_action({"thought": "try", "action_name": "unknown_tool", "action_input": {}})

    assert result.ok is False
    assert result.action is None
    assert "unknown tool" in result.error


def test_collector_invalid_json_action_increments_invalid_action_count(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=task,
        policy=InvalidJsonPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=1,
        run_hidden=False,
    )

    assert result["invalid_action_count"] == 1
    assert result["reward"]["action_stats"]["invalid_json_count"] == 1


def test_noop_policy_creates_trajectory_without_mutating_original(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()
    before = compute_repo_checksum(task)

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=task,
        policy=NoopPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=3,
        run_hidden=False,
    )

    assert result["task_id"] == "task_001"
    assert result["original_repo_unchanged"] is True
    assert compute_repo_checksum(task) == before
    assert Path(result["trajectory_path"]).exists()
    assert result["steps"] >= 1
    assert result["stop_reason"] == "policy_stop"


def test_scripted_policy_runs_tree_search_and_read_or_stop(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=task,
        policy=ScriptedSearchPatchPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=6,
        run_hidden=False,
    )

    actions = [step["action_name"] for step in result["observations"] if step["type"] == "step"]
    assert "repo_tree" in actions
    assert "search_repo" in actions
    assert "read_file" in actions or "stop" in actions
    assert result["original_repo_unchanged"] is True


def test_rollout_result_is_json_serializable(tmp_path: Path):
    task = Path("data/mini_repo_debug/repos/task_001").resolve()

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=task,
        policy=NoopPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=2,
    )

    json.dumps(result)
