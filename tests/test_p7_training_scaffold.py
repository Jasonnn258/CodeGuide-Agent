import json
from pathlib import Path

from codeguide_agent.dataset.export_training_candidates import export_training_candidates
from codeguide_agent.dataset.prepare_training_package import prepare_training_package
from codeguide_agent.training.data import FORBIDDEN_MODEL_TERMS, load_training_package
from codeguide_agent.training.dry_run_train import run_dry_train
from codeguide_agent.training.replay_eval import replay_run
from codeguide_agent.testing.mini_repo_trajectory_fixture import build_mini_repo_trajectory_fixture


def _prepare_package(tmp_path: Path) -> Path:
    exports = tmp_path / "exports"
    package = tmp_path / "train_package"
    export_training_candidates("data/mini_repo_debug", exports, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    prepare_training_package("data/mini_repo_debug", package, exports_dir=exports)
    return package


def test_sft_loader_reads_train_and_eval_records(tmp_path: Path):
    package = _prepare_package(tmp_path)
    dataset = load_training_package(package, mode="sft", batch_size=4)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))

    assert dataset.mode == "sft"
    assert len(dataset.train_records) == manifest["counts"]["sft_train"]
    assert len(dataset.eval_records) == manifest["counts"]["sft_eval"]
    assert len(dataset.train_records) + len(dataset.eval_records) > 19
    assert dataset.batch_count == (len(dataset.train_records) + 3) // 4
    assert dataset.preview_batch
    assert dataset.quality_gate["passed"] is True


def test_preference_loader_reads_chosen_rejected_records(tmp_path: Path):
    package = _prepare_package(tmp_path)
    dataset = load_training_package(package, mode="preference", batch_size=2)

    assert dataset.mode == "preference"
    assert len(dataset.train_records) == 1
    assert len(dataset.eval_records) == 0
    record = dataset.train_records[0]
    assert record["task_id"] == "task_009"
    assert "chosen" in record
    assert "rejected" in record


def test_loader_sanitization_gate_rejects_forbidden_terms(tmp_path: Path):
    package = _prepare_package(tmp_path)
    sft_train = package / "sft_train.jsonl"
    sft_train.write_text(
        sft_train.read_text(encoding="utf-8") + json.dumps({"record_type": "codeguide_sft_v1", "task_id": "task_001", "bad": "tests_hidden"}) + "\n",
        encoding="utf-8",
    )

    try:
        load_training_package(package, mode="sft")
    except ValueError as exc:
        assert any(term in str(exc) for term in FORBIDDEN_MODEL_TERMS)
    else:
        raise AssertionError("expected sanitization failure")


def test_dry_run_sft_creates_run_summary(tmp_path: Path):
    package = _prepare_package(tmp_path)
    result = run_dry_train(package, mode="sft", out_dir=tmp_path / "runs" / "sft")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))

    summary_path = Path(result["summary_path"])
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["mode"] == "sft"
    assert summary["dry_run"] is True
    assert summary["train_records"] == manifest["counts"]["sft_train"]
    assert summary["batch_count"] == (manifest["counts"]["sft_train"] + 3) // 4
    assert Path(summary["formatted_preview_path"]).exists()


def test_dry_run_preference_creates_chosen_rejected_preview(tmp_path: Path):
    package = _prepare_package(tmp_path)
    result = run_dry_train(package, mode="preference", out_dir=tmp_path / "runs" / "preference")

    preview = Path(result["formatted_preview_path"]).read_text(encoding="utf-8")
    assert "chosen" in preview
    assert "rejected" in preview
    assert result["train_records"] == 1


def test_replay_scaffold_smoke_test(tmp_path: Path):
    package = _prepare_package(tmp_path)
    run = run_dry_train(package, mode="sft", out_dir=tmp_path / "runs" / "sft")
    result = replay_run(run["run_dir"], root="data/mini_repo_debug")

    assert result["passed"] is True
    assert result["checked_records"] > 0
    assert result["hidden_tests_run"] is False
    assert Path(result["report_path"]).exists()
