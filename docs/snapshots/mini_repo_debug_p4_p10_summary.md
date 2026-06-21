# Mini-Repo-Debug P4-P10 Summary

## Scope

- P4: expanded Mini-Repo-Debug to 20 tasks.
- P5: exported SFT/preference candidates.
- P6: built train-ready package with quality gate.
- P7: added dry-run training scaffold.
- P8: added experiment loop scaffold.
- P9: expanded preference candidates.
- P10: added one-command offline validation and project snapshot.
- No real model training, GRPO, or paid API call is required for this snapshot.

## Dataset

- task_count: `20`

## Real LLM Baseline

- num_tasks: `20`
- success_rate: `0.95`
- public_pass_rate: `1.0`
- hidden_pass_rate: `0.95`
- public_pass_hidden_fail_rate: `0.05`
- leakage_rate: `0.0`
- syntax_error_rate: `0.0`
- original_repo_unchanged_rate: `1.0`
- invalid_action_rate: `0.05`
- average_llm_calls: `3.4`
- hidden_failure_type_counts: `{'hidden_assertion_fail': 1, 'none': 19}`
- patch_generalization_risk_counts: `{'low': 19, 'medium': 1}`

## P5 Exports

- sft_records: `19`
- preference_pairs: `1`
- task_009_preference_pair_generated: `True`

## P9 Preference Bank

- preference_candidates: `23`
- task_coverage: `['task_001', 'task_002', 'task_003', 'task_004', 'task_005', 'task_006', 'task_007', 'task_008', 'task_009', 'task_010', 'task_011', 'task_012', 'task_013', 'task_014', 'task_015', 'task_016', 'task_017', 'task_018', 'task_019', 'task_020']`
- rejection_reason_counts: `{'invalid_action': 2, 'no_patch': 20, 'public_pass_hidden_assertion_fail': 1}`

## P6/P9 Train Package


## P8/P10 Experiment Smoke

- experiment_dir: `experiments/mini_repo_debug/p10_pipeline_smoke`
- checked_tasks: `20`
- predicted_tasks: `19`
- patch_inspection_pass_rate: `0.95`
- leakage_rate: `0.0`
- checked_records: `20`
- passed: `False`
- hidden_tests_run: `False`

## Current Known Limitations

- Preference candidates are expanded, but many pairs are original-buggy/no-patch vs gold; useful for pipeline checks, not yet rich enough for serious DPO.
- Current training loop is scaffold/dry-run only; no real SFT/DPO/GRPO has been run.
- Hidden tests remain evaluator-only and are not model-facing.
