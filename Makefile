.PHONY: test clean-check audit scale-report task-skeletons validate-pipeline clean-generated p5 p6 p9 dry-run-sft dry-run-pref

test:
	python -m codeguide_agent.testing.simple_pytest tests -q

clean-check:
	bash scripts/check_tests_without_generated_trajectories.sh

audit:
	bash scripts/audit_model_facing_artifacts.sh

scale-report:
	python scripts/report_dataset_scale.py

task-skeletons:
	python scripts/generate_task_skeletons.py

validate-pipeline:
	bash scripts/validate_mini_repo_pipeline.sh

clean-generated:
	bash scripts/clean_mini_repo_generated.sh

p5:
	python -m codeguide_agent.dataset.export_training_candidates --root data/mini_repo_debug --out data/mini_repo_debug/exports

p9:
	python -m codeguide_agent.dataset.expand_preference_candidates --root data/mini_repo_debug --out data/mini_repo_debug/preference_bank

p6:
	python -m codeguide_agent.dataset.prepare_training_package --root data/mini_repo_debug --out data/mini_repo_debug/train_package

dry-run-sft:
	python -m codeguide_agent.training.dry_run_train --package data/mini_repo_debug/train_package --mode sft

dry-run-pref:
	python -m codeguide_agent.training.dry_run_train --package data/mini_repo_debug/train_package --mode preference
