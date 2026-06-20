import json
from pathlib import Path

from codeguide_agent.eval_compare import compare_policies
from codeguide_agent.rollout.collector import RolloutCollector
from codeguide_agent.rollout.policy import GoldPatchPolicy, HeuristicLocalizePolicy


def test_heuristic_policy_localizes_without_forbidden_access_or_edits(tmp_path: Path):
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=HeuristicLocalizePolicy(),
        temp_root=tmp_path / "eval",
        max_steps=8,
        run_hidden=False,
    )

    actions = [row["action_name"] for row in result["observations"] if row.get("type") == "step"]
    visible = json.dumps(result["observations"], sort_keys=True)
    assert "repo_tree" in actions
    assert "search_repo" in actions
    assert "read_file" in actions
    assert "edit_file" not in actions
    assert "apply_gold_patch" not in actions
    assert result["edited_files"] == []
    assert "metadata.json" not in visible
    assert "gold.patch" not in visible
    assert "tests_hidden" not in visible
    assert result["reward"]["forbidden_file_access"] is False


def test_heuristic_policy_gets_process_localization_hit_on_current_dataset(tmp_path: Path):
    tasks = sorted(Path("data/mini_repo_debug/repos").glob("task_*"))
    results = [
        RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
            task=task,
            policy=HeuristicLocalizePolicy(),
            temp_root=tmp_path / "eval",
            max_steps=8,
            run_hidden=False,
        )
        for task in tasks
    ]

    assert any(result["reward"]["gold_file_hit_at_3"] for result in results)
    assert any(result["reward"]["gold_function_hit_at_3"] for result in results)


def test_gold_patch_can_patch_without_process_localization(tmp_path: Path):
    result = RolloutCollector(trajectories_dir=tmp_path / "trajectories").collect(
        task=Path("data/mini_repo_debug/repos/task_001").resolve(),
        policy=GoldPatchPolicy(),
        temp_root=tmp_path / "eval",
        max_steps=4,
        run_hidden=False,
    )

    assert result["reward"]["gold_file_patched"] is True
    assert result["reward"]["gold_file_hit_at_3"] is False


def test_eval_compare_writes_report_for_policies(tmp_path: Path):
    report = compare_policies(
        root="data/mini_repo_debug",
        policies=["noop", "heuristic"],
        limit=2,
        report_path=tmp_path / "eval_compare.json",
        temp_root=tmp_path / "eval",
        trajectories_dir=tmp_path / "trajectories",
    )

    assert Path(report["report_path"]).exists()
    assert set(report["policies"]) == {"noop", "heuristic"}
    assert "gold_file_hit_at_3_rate" in report["summary"]["heuristic"]
