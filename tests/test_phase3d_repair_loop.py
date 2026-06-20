from pathlib import Path

from codeguide_agent.rollout.actions import Action
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import BasePolicy


TASK = Path("data/mini_repo_debug/repos/task_001").resolve()


class SequencePolicy(BasePolicy):
    name = "llm"

    def __init__(self, actions):
        self.actions = list(actions)

    def next_action(self, state):
        if self.actions:
            return self.actions.pop(0)
        return Action("stop", "stop", {"reason": "done"})


def test_failed_edit_requires_read_before_another_edit(tmp_path: Path):
    policy = SequencePolicy(
        [
            Action("read first", "read_file", {"file_path": "src/config_loader.py"}),
            Action("bad edit", "edit_file", {"file_path": "src/config_loader.py", "old_text": "missing", "new_text": "x"}),
            Action("retry without read", "edit_file", {"file_path": "src/config_loader.py", "old_text": "return json.loads(text)", "new_text": "return {}"}),
            Action("stop", "stop", {"reason": "done"}),
        ]
    )

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=5,
    )

    assert result["edit_retry_count"] == 1
    assert result["invalid_action_count"] >= 1
    assert result["edited_files"] == []


def test_repeated_edit_is_counted_and_rejected(tmp_path: Path):
    old_text = "return json.loads(text)"
    policy = SequencePolicy(
        [
            Action("read first", "read_file", {"file_path": "src/config_loader.py"}),
            Action("edit", "edit_file", {"file_path": "src/config_loader.py", "old_text": old_text, "new_text": "return {}"}),
            Action("repeat", "edit_file", {"file_path": "src/config_loader.py", "old_text": old_text, "new_text": "return {'x': 1}"}),
            Action("stop", "stop", {"reason": "done"}),
        ]
    )

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=5,
    )

    assert result["repeated_edit_count"] == 1
    assert result["invalid_action_count"] >= 1
    assert result["repair_loop_violation_count"] == 1


def test_rejected_edit_after_success_does_not_switch_to_failed_edit_state(tmp_path: Path):
    old_text = "return json.loads(text)"
    policy = SequencePolicy(
        [
            Action("read first", "read_file", {"file_path": "src/config_loader.py"}),
            Action("edit", "edit_file", {"file_path": "src/config_loader.py", "old_text": old_text, "new_text": "return {}"}),
            Action("repeat rejected", "edit_file", {"file_path": "src/config_loader.py", "old_text": old_text, "new_text": "return {'x': 1}"}),
            Action("read after rejection", "read_file", {"file_path": "src/config_loader.py"}),
            Action("stop", "stop", {"reason": "done"}),
        ]
    )

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=5,
    )

    assert result["repeated_edit_count"] == 1
    assert result["edit_retry_count"] == 0
    assert result["repair_loop_violation_count"] == 1


def test_successful_edit_triggers_auto_public_test(tmp_path: Path):
    policy = SequencePolicy(
        [
            Action("read first", "read_file", {"file_path": "src/config_loader.py"}),
            Action("edit", "edit_file", {"file_path": "src/config_loader.py", "old_text": "return json.loads(text)", "new_text": "return {}"}),
            Action("stop", "stop", {"reason": "done"}),
        ]
    )

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=4,
    )

    assert result["auto_public_test_after_edit_count"] == 1
    assert result["final_test_ran"] is True


def test_syntax_error_is_detected_without_leakage(tmp_path: Path):
    policy = SequencePolicy(
        [
            Action("read first", "read_file", {"file_path": "src/config_loader.py"}),
            Action(
                "break syntax",
                "edit_file",
                {
                    "file_path": "src/config_loader.py",
                    "old_text": "    return json.loads(text)",
                    "new_text": "    if True:\n    return json.loads(text)",
                },
            ),
            Action("stop", "stop", {"reason": "done"}),
        ]
    )

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=4,
    )

    assert result["reward"]["syntax_error"] is True
    assert result["reward"]["syntax_error_files"] == ["src/config_loader.py"]
    assert result["reward"]["leakage_detected"] is False


def test_incomplete_stop_is_marked_before_public_test_and_diff(tmp_path: Path):
    policy = SequencePolicy([Action("stop too early", "stop", {"reason": "uncertain"})])

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=2,
    )

    assert result["reward"]["incomplete_stop"] is True
    assert result["reward"]["final_test_ran"] is True
    assert result["reward"]["final_diff_collected"] is True


def test_real_edit_failure_still_requires_read_file_before_retry(tmp_path: Path):
    policy = SequencePolicy(
        [
            Action("read first", "read_file", {"file_path": "src/config_loader.py"}),
            Action("real failure", "edit_file", {"file_path": "src/config_loader.py", "old_text": "not present", "new_text": "x"}),
            Action("retry blocked", "edit_file", {"file_path": "src/config_loader.py", "old_text": "return json.loads(text)", "new_text": "return {}"}),
            Action("read required", "read_file", {"file_path": "src/config_loader.py"}),
            Action("retry now allowed", "edit_file", {"file_path": "src/config_loader.py", "old_text": "return json.loads(text)", "new_text": "return {}"}),
            Action("stop", "stop", {"reason": "done"}),
        ]
    )

    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        TASK,
        policy,
        temp_root=tmp_path / "eval",
        max_steps=7,
    )

    assert result["edit_retry_count"] == 1
    assert result["repair_loop_violation_count"] == 1
    assert result["edited_files"] == ["src/config_loader.py"]
