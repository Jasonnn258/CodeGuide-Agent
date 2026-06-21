.PHONY: test clean-check audit scale-report task-skeletons promotion-report promotion-check validate-pipeline clean-generated p5 p6 p9 dry-run-sft dry-run-pref promote-task rollout-plan readiness training-data training-preflight train-sft train-sft-smoke dpo-readiness docs-check canonical-check expansion-check

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

promotion-report:
	python scripts/check_planned_task_ready.py

promotion-check:
	python scripts/check_planned_task_ready.py --task-id $(TASK)

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

promote-task:
	python scripts/promote_planned_task.py --task-id $(TASK)

rollout-plan:
	python scripts/build_rollout_batch_plan.py

readiness:
	python scripts/training_readiness_gate.py

training-data:
	python -m codeguide_agent.training.build_hf_training_data --package data/mini_repo_debug/train_package --out data/mini_repo_debug/hf_training

training-preflight:
	python scripts/training_preflight.py

train-sft:
	python -m codeguide_agent.training.real_sft_lora_train --config configs/training/sft_qwen2_5_coder_lora.json

train-sft-smoke:
	python -m codeguide_agent.training.real_sft_lora_train --config configs/training/sft_smoke_tiny.json --max-steps 3

dpo-readiness:
	python -m codeguide_agent.training.real_dpo_train --data-dir data/mini_repo_debug/hf_training

docs-check:
	python scripts/check_doc_rendering.py

canonical-check:
	python scripts/check_canonical_training_pipeline.py

expansion-check:
	python scripts/check_expansion_backlog.py
