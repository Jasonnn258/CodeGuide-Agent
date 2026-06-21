import json
from pathlib import Path

from codeguide_agent.testing.mini_repo_trajectory_fixture import build_mini_repo_trajectory_fixture

from codeguide_agent.dataset.expand_preference_candidates import _rejection_reason, expand_preference_candidates
from codeguide_agent.dataset.prepare_training_package import prepare_training_package, validate_training_package
from codeguide_agent.eval.run_eval import discover_tasks


FORBIDDEN_TERMS = ("tests_hidden", "metadata.json", "gold.patch", "apply_gold_patch", '"stdout"', '"stderr"')


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_expand_preference_candidates_smoke_and_schema(tmp_path: Path):
    out = tmp_path / "preference_bank"
    summary = expand_preference_candidates("data/mini_repo_debug", out, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    records = _read_jsonl(out / "preference_candidates.jsonl")

    assert summary["candidate_count"] == len(records)
    assert summary["candidate_count"] >= 20
    assert (out / "preference_bank_summary.json").exists()
    assert (out / "rejection_taxonomy.json").exists()
    for record in records:
        assert record["record_type"] == "preference_pair_candidate"
        assert record["task_id"].startswith("task_")
        assert record["chosen"]["final_patch"].startswith("diff --git")
        assert "rejection_reason" in record
        assert record["reason_labels"]
        assert "public_pass" in record["evaluator_metadata"]
        assert "hidden_pass" in record["evaluator_metadata"]


def test_preference_bank_is_sanitized(tmp_path: Path):
    out = tmp_path / "preference_bank"
    expand_preference_candidates("data/mini_repo_debug", out, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    text = (out / "preference_candidates.jsonl").read_text(encoding="utf-8")

    for term in FORBIDDEN_TERMS:
        assert term not in text


def test_preference_bank_dedupes_identical_pairs(tmp_path: Path):
    out = tmp_path / "preference_bank"
    expand_preference_candidates("data/mini_repo_debug", out, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    records = _read_jsonl(out / "preference_candidates.jsonl")
    keys = [
        (
            record["task_id"],
            record["source_policy"],
            record["rejection_reason"],
            record["chosen"]["final_patch"],
            record["rejected"].get("final_patch", ""),
        )
        for record in records
    ]

    assert len(keys) == len(set(keys))


def test_public_pass_hidden_fail_no_patch_is_hard_preference_reason():
    reward = {
        "public_pass": True,
        "hidden_pass": False,
        "public_pass_hidden_fail": True,
        "hidden_failure_type": "hidden_assertion_fail",
    }

    assert _rejection_reason(reward, "", {"gold_files": ["src/example.py"]}) == "public_pass_hidden_assertion_fail"


def test_task_009_public_pass_hidden_fail_pair_is_preserved(tmp_path: Path):
    out = tmp_path / "preference_bank"
    expand_preference_candidates("data/mini_repo_debug", out, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    records = _read_jsonl(out / "preference_candidates.jsonl")

    task_009 = [
        record
        for record in records
        if record["task_id"] == "task_009" and record["rejection_reason"] == "public_pass_hidden_assertion_fail"
    ]
    assert task_009
    assert task_009[0]["source_policy"] == "llm"
    assert task_009[0]["evaluator_metadata"]["public_pass"] is True
    assert task_009[0]["evaluator_metadata"]["hidden_pass"] is False


def test_original_buggy_vs_gold_pair_exists_for_each_task(tmp_path: Path):
    out = tmp_path / "preference_bank"
    expand_preference_candidates("data/mini_repo_debug", out, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    records = _read_jsonl(out / "preference_candidates.jsonl")
    original_pairs = [record for record in records if record["source_policy"] == "original_buggy"]

    assert len(original_pairs) == len(discover_tasks("data/mini_repo_debug"))
    assert {record["rejection_reason"] for record in original_pairs} == {"no_patch"}


def test_prepare_training_package_can_use_preference_bank(tmp_path: Path):
    preference_bank = tmp_path / "preference_bank"
    package = tmp_path / "train_package"
    expand_preference_candidates("data/mini_repo_debug", preference_bank)
    manifest = prepare_training_package(
        "data/mini_repo_debug",
        package,
        preference_bank=preference_bank / "preference_candidates.jsonl",
    )

    quality = validate_training_package("data/mini_repo_debug", package)
    assert quality["passed"] is True
    assert manifest["counts"]["preference_total"] >= 20
    assert manifest["preference_source"]["kind"] == "preference_bank"
