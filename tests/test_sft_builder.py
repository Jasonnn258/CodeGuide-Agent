import json
from pathlib import Path

from codeguide_agent.data_builders.build_sft import build_sft_dataset


def test_sft_builder_writes_valid_jsonl_messages(tmp_path: Path):
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir()
    trajectory_file = trajectories / "task_001_scripted.jsonl"
    trajectory_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "step",
                        "task_id": "task_001",
                        "trajectory_id": "traj",
                        "thought": "inspect",
                        "action_name": "repo_tree",
                        "action_input": {},
                        "observation": {"status": "success", "entries": ["src/app.py"]},
                    }
                ),
                json.dumps(
                    {
                        "type": "final",
                        "task_id": "task_001",
                        "trajectory_id": "traj",
                        "final_patch": "diff --git a/src/app.py b/src/app.py",
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
    sample = json.loads(output.read_text(encoding="utf-8").strip())
    assert sample["messages"][0]["role"] == "system"
    assert "repo-level code repair agent" in sample["messages"][0]["content"]
    assert sample["metadata"]["task_id"] == "task_001"


def test_sft_builder_does_not_leak_hidden_test_content(tmp_path: Path):
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir()
    (trajectories / "task_001_scripted.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "step",
                        "task_id": "task_001",
                        "trajectory_id": "traj",
                        "thought": "run tests",
                        "action_name": "run_test",
                        "action_input": {"command": "python -m pytest tests_hidden -q"},
                        "observation": {
                            "status": "success",
                            "stdout": "tests_hidden/test_secret.py::test_secret_expected_value failed",
                            "stderr": "",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "final",
                        "task_id": "task_001",
                        "trajectory_id": "traj",
                        "final_patch": "patch",
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

    build_sft_dataset(trajectories, output)

    text = output.read_text(encoding="utf-8")
    assert "tests_hidden" not in text
    assert "test_secret_expected_value" not in text
