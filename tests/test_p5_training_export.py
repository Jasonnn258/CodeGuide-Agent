import json
from pathlib import Path

from codeguide_agent.dataset.export_training_candidates import (
    FORBIDDEN_EXPORT_TERMS,
    export_training_candidates,
    load_trajectory,
    sanitize_trajectory_rows,
)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_p5_export_writes_expected_files_and_schema(tmp_path: Path):
    result = export_training_candidates("data/mini_repo_debug", tmp_path)

    sft_path = tmp_path / "p5_sft_rollouts.jsonl"
    prefs_path = tmp_path / "p5_preference_pairs.jsonl"
    summary_path = tmp_path / "p5_export_summary.json"

    assert sft_path.exists()
    assert prefs_path.exists()
    assert summary_path.exists()
    assert result["sft_records"] >= 1

    sft_record = _read_jsonl(sft_path)[0]
    assert sft_record["record_type"] == "sft_rollout_candidate"
    assert sft_record["task_id"]
    assert isinstance(sft_record["actions"], list)
    assert sft_record["final_patch"].startswith("diff --git")
    assert sft_record["reward_summary"]["public_pass"] is True
    assert sft_record["reward_summary"]["hidden_pass"] is True


def test_p5_export_sanitizes_hidden_paths_and_outputs(tmp_path: Path):
    export_training_candidates("data/mini_repo_debug", tmp_path)

    exported_text = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.glob("p5_*"))

    for forbidden in FORBIDDEN_EXPORT_TERMS:
        assert forbidden not in exported_text
    assert "test_explicit_starting_tags_are_copied_and_extended" not in exported_text
    assert "SECRET_HIDDEN" not in exported_text


def test_task_009_preference_pair_is_generated_when_failed_llm_exists(tmp_path: Path):
    result = export_training_candidates("data/mini_repo_debug", tmp_path)
    pairs = _read_jsonl(tmp_path / "p5_preference_pairs.jsonl")
    task_009 = [pair for pair in pairs if pair["task_id"] == "task_009"]

    assert result["task_009_preference_pair_generated"] is True
    assert task_009
    pair = task_009[0]
    assert "hidden_assertion_fail" in pair["reason_labels"]
    assert pair["rejected"]["reward_summary"]["public_pass"] is True
    assert pair["rejected"]["reward_summary"]["hidden_pass"] is False
    assert pair["chosen"]["final_patch"].startswith("diff --git")
    assert "apply_gold_patch" not in json.dumps(pair["chosen"], sort_keys=True)


def test_sanitize_trajectory_rows_drops_hidden_verifier_payloads():
    rows = [
        {
            "type": "step",
            "action_name": "run_test",
            "action_input": {"command": "python -m pytest tests_hidden -q", "phase": "final_hidden"},
            "observation": {"stdout": "SECRET_HIDDEN_OUTPUT", "stderr": "hidden stack"},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/tags.py"},
            "observation": {"content": "def collect_tags():\n    pass\n", "status": "success"},
        },
    ]

    sanitized = sanitize_trajectory_rows(rows)
    text = json.dumps(sanitized, sort_keys=True)

    assert len(sanitized) == 1
    assert "SECRET_HIDDEN_OUTPUT" not in text
    assert "tests_hidden" not in text


def test_load_trajectory_reads_final_row():
    rows = load_trajectory("data/mini_repo_debug/trajectories/task_009_llm.jsonl")

    assert rows[-1]["type"] == "final"
    assert rows[-1]["reward"]["public_pass_hidden_fail"] is True
