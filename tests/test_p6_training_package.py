import json
from pathlib import Path

from codeguide_agent.dataset.export_training_candidates import export_training_candidates
from codeguide_agent.dataset.prepare_training_package import (
    FORBIDDEN_PACKAGE_TERMS,
    prepare_training_package,
    validate_training_package,
)
from codeguide_agent.testing.mini_repo_trajectory_fixture import build_mini_repo_trajectory_fixture


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _export_training_candidates_for_test(tmp_path: Path, out_dir: Path):
    trajectories_dir = build_mini_repo_trajectory_fixture(tmp_path)
    return export_training_candidates("data/mini_repo_debug", out_dir, trajectories_dir=trajectories_dir)


def test_prepare_training_package_writes_expected_files(tmp_path: Path):
    _export_training_candidates_for_test(tmp_path, tmp_path / "exports")
    result = prepare_training_package("data/mini_repo_debug", tmp_path / "package", exports_dir=tmp_path / "exports")

    for name in [
        "sft_train.jsonl",
        "sft_eval.jsonl",
        "preference_train.jsonl",
        "preference_eval.jsonl",
        "manifest.json",
        "data_card.md",
    ]:
        assert (tmp_path / "package" / name).exists()
    assert result["quality_gate"]["passed"] is True
    assert result["counts"]["sft_total"] > 19
    assert result["sft_source_counts"]["sft_rollout_candidate"] > 0
    assert result["sft_source_counts"]["gold_patch_sft_candidate"] > 0
    assert sum(result["sft_source_counts"].values()) == result["counts"]["sft_total"]
    assert result["counts"]["preference_total"] == 1


def test_training_package_schema_and_success_filter(tmp_path: Path):
    _export_training_candidates_for_test(tmp_path, tmp_path / "exports")
    prepare_training_package("data/mini_repo_debug", tmp_path / "package", exports_dir=tmp_path / "exports")

    sft_records = _read_jsonl(tmp_path / "package" / "sft_train.jsonl") + _read_jsonl(tmp_path / "package" / "sft_eval.jsonl")
    assert sft_records
    record = sft_records[0]
    assert record["record_type"] == "codeguide_sft_v1"
    assert [message["role"] for message in record["messages"]] == ["system", "user", "assistant"]
    assert isinstance(record["tool_trace"], list)
    assert record["final_patch"].startswith("diff --git")
    assert record["reward_summary"]["public_pass"] is True
    assert record["reward_summary"]["hidden_pass"] is True
    assert record["quality"]["source_success"] is True


def test_training_package_includes_gold_reference_sft_records(tmp_path: Path):
    _export_training_candidates_for_test(tmp_path, tmp_path / "exports")
    result = prepare_training_package("data/mini_repo_debug", tmp_path / "package", exports_dir=tmp_path / "exports")

    sft_records = _read_jsonl(tmp_path / "package" / "sft_train.jsonl") + _read_jsonl(tmp_path / "package" / "sft_eval.jsonl")
    gold_records = [record for record in sft_records if record["source_record_type"] == "gold_patch_sft_candidate"]

    assert len(gold_records) == result["sft_source_counts"]["gold_patch_sft_candidate"]
    assert gold_records
    record = gold_records[0]
    assert record["final_patch"].startswith("diff --git")
    assert record["reward_summary"]["public_pass"] is True
    assert record["reward_summary"]["hidden_pass"] is True
    assert record["quality"]["source_success"] is True


def test_training_package_has_deterministic_task_split_without_overlap(tmp_path: Path):
    _export_training_candidates_for_test(tmp_path, tmp_path / "exports")
    first = prepare_training_package("data/mini_repo_debug", tmp_path / "package_a", exports_dir=tmp_path / "exports")
    second = prepare_training_package("data/mini_repo_debug", tmp_path / "package_b", exports_dir=tmp_path / "exports")

    assert first["splits"] == second["splits"]
    assert not (set(first["splits"]["sft_train_task_ids"]) & set(first["splits"]["sft_eval_task_ids"]))
    assert not (set(first["splits"]["preference_train_task_ids"]) & set(first["splits"]["preference_eval_task_ids"]))


def test_training_package_sanitizes_model_facing_files(tmp_path: Path):
    _export_training_candidates_for_test(tmp_path, tmp_path / "exports")
    prepare_training_package("data/mini_repo_debug", tmp_path / "package", exports_dir=tmp_path / "exports")

    model_text = "\n".join(
        (tmp_path / "package" / name).read_text(encoding="utf-8")
        for name in ["sft_train.jsonl", "sft_eval.jsonl", "preference_train.jsonl", "preference_eval.jsonl"]
    )
    for forbidden in FORBIDDEN_PACKAGE_TERMS:
        assert forbidden not in model_text
    assert "stdout" not in model_text
    assert "stderr" not in model_text
    assert "test_explicit_starting_tags_are_copied_and_extended" not in model_text


def test_task_009_preference_record_is_packaged(tmp_path: Path):
    _export_training_candidates_for_test(tmp_path, tmp_path / "exports")
    result = prepare_training_package("data/mini_repo_debug", tmp_path / "package", exports_dir=tmp_path / "exports")
    prefs = _read_jsonl(tmp_path / "package" / "preference_train.jsonl") + _read_jsonl(
        tmp_path / "package" / "preference_eval.jsonl"
    )
    task_009 = [record for record in prefs if record["task_id"] == "task_009"]

    assert result["counts"]["preference_total"] == 1
    assert task_009
    record = task_009[0]
    assert record["record_type"] == "codeguide_preference_v1"
    assert "hidden_assertion_fail" in record["reason_labels"]
    assert record["rejected"]["reward_summary"]["public_pass"] is True
    assert record["rejected"]["reward_summary"]["hidden_pass"] is False
    assert record["chosen"]["final_patch"].startswith("diff --git")


def test_validate_training_package_flags_bad_schema(tmp_path: Path):
    package = tmp_path / "package"
    package.mkdir()
    for name in ["sft_train.jsonl", "sft_eval.jsonl", "preference_train.jsonl", "preference_eval.jsonl"]:
        (package / name).write_text("", encoding="utf-8")
    (package / "sft_train.jsonl").write_text(json.dumps({"record_type": "bad", "task_id": "task_999"}) + "\n", encoding="utf-8")

    result = validate_training_package("data/mini_repo_debug", package)

    assert result["passed"] is False
    assert result["errors"]
