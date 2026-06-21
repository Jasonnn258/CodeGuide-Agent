import json
from pathlib import Path

from codeguide_agent.testing.mini_repo_trajectory_fixture import build_mini_repo_trajectory_fixture

from codeguide_agent.dataset.export_training_candidates import export_training_candidates
from codeguide_agent.dataset.prepare_training_package import prepare_training_package
from codeguide_agent.training.create_experiment import create_experiment
from codeguide_agent.training.eval_experiment import evaluate_experiment
from codeguide_agent.training.mock_train_artifact import create_mock_artifact
from codeguide_agent.training.trained_policy import TrainedPatchPolicy


def _prepare_package(tmp_path: Path) -> Path:
    exports = tmp_path / "exports"
    package = tmp_path / "train_package"
    export_training_candidates("data/mini_repo_debug", exports, trajectories_dir=build_mini_repo_trajectory_fixture(tmp_path))
    prepare_training_package("data/mini_repo_debug", package, exports_dir=exports)
    return package


def test_create_experiment_writes_registry_files(tmp_path: Path):
    package = _prepare_package(tmp_path)
    result = create_experiment(package, mode="sft", run_name="p8_test", experiments_root=tmp_path / "experiments")

    run_dir = Path(result["run_dir"])
    for name in ["config.json", "metrics.json", "artifacts.json", "replay_report.json", "eval_summary.json"]:
        assert (run_dir / name).exists()
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["run_name"] == "p8_test"
    assert config["mode"] == "sft"
    assert config["dataset_hash"]
    assert config["sanitization"]["passed"] is True


def test_mock_artifact_records_metadata_without_weights(tmp_path: Path):
    package = _prepare_package(tmp_path)
    experiment = create_experiment(package, mode="sft", run_name="p8_test", experiments_root=tmp_path / "experiments")
    result = create_mock_artifact(experiment["run_dir"])

    artifacts = json.loads((Path(experiment["run_dir"]) / "artifacts.json").read_text(encoding="utf-8"))
    assert result["artifact_type"] == "mock_adapter"
    assert artifacts["artifact_type"] == "mock_adapter"
    assert artifacts["contains_model_weights"] is False
    assert artifacts["patch_candidates"]


def test_trained_policy_loads_mock_patch_candidates(tmp_path: Path):
    package = _prepare_package(tmp_path)
    experiment = create_experiment(package, mode="sft", run_name="p8_test", experiments_root=tmp_path / "experiments")
    create_mock_artifact(experiment["run_dir"])

    policy = TrainedPatchPolicy(experiment["run_dir"])
    patch = policy.predict_patch("task_001")

    assert policy.name == "trained"
    assert patch.startswith("diff --git")


def test_eval_experiment_writes_eval_summary(tmp_path: Path):
    package = _prepare_package(tmp_path)
    experiment = create_experiment(package, mode="sft", run_name="p8_test", experiments_root=tmp_path / "experiments")
    create_mock_artifact(experiment["run_dir"])

    result = evaluate_experiment(experiment["run_dir"], root="data/mini_repo_debug", limit=3)

    assert result["checked_tasks"] == 3
    assert result["hidden_tests_run"] is False
    assert result["leakage_rate"] == 0.0
    assert Path(result["eval_summary_path"]).exists()


def test_experiment_artifacts_are_sanitized(tmp_path: Path):
    package = _prepare_package(tmp_path)
    experiment = create_experiment(package, mode="sft", run_name="p8_test", experiments_root=tmp_path / "experiments")
    create_mock_artifact(experiment["run_dir"])
    evaluate_experiment(experiment["run_dir"], root="data/mini_repo_debug", limit=2)

    text = "\n".join(path.read_text(encoding="utf-8") for path in Path(experiment["run_dir"]).glob("*.json"))
    assert "tests_hidden" not in text
    assert "metadata.json" not in text
    assert "gold.patch" not in text
    assert "apply_gold_patch" not in text
