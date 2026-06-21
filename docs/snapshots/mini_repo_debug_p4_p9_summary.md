# Mini-Repo-Debug P4-P9 Summary

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

## P5 Export

- preference_output: `data/mini_repo_debug/exports/p5_preference_pairs.jsonl`
- preference_pairs: `1`
- root: `data/mini_repo_debug`
- sft_output: `data/mini_repo_debug/exports/p5_sft_rollouts.jsonl`
- sft_records: `19`
- summary_output: `data/mini_repo_debug/exports/p5_export_summary.json`
- task_009_preference_pair_generated: `True`
- tasks_seen: `20`
- trajectories_dir: `data/mini_repo_debug/trajectories`

## P6/P9 Train Package


## P9 Preference Bank

- candidate_count: `23`
- candidate_output: `data/mini_repo_debug/preference_bank/preference_candidates.jsonl`
- dedupe: `{'duplicates_removed': 60, 'input_candidates': 83, 'output_candidates': 23}`
- quality_gate: `{'errors': [], 'passed': True}`
- rejection_reason_counts: `{'invalid_action': 2, 'no_patch': 20, 'public_pass_hidden_assertion_fail': 1}`
- root: `data/mini_repo_debug`
- sanitization: `{'forbidden_path_terms_redacted': 4, 'passed': True, 'raw_test_stdout_stderr_exported': False}`
- skipped: `{'missing_or_unusable_llm': 17}`
- source_policy_counts: `{'llm': 3, 'original_buggy': 20}`
- summary_output: `data/mini_repo_debug/preference_bank/preference_bank_summary.json`
- task_coverage: `['task_001', 'task_002', 'task_003', 'task_004', 'task_005', 'task_006', 'task_007', 'task_008', 'task_009', 'task_010', 'task_011', 'task_012', 'task_013', 'task_014', 'task_015', 'task_016', 'task_017', 'task_018', 'task_019', 'task_020']`
- task_coverage_count: `20`
- taxonomy_output: `data/mini_repo_debug/preference_bank/rejection_taxonomy.json`
- trajectories_dir: `data/mini_repo_debug/trajectories`

## Status

- P4: expanded Mini-Repo-Debug to 20 tasks.
- P5: exported SFT/preference candidates.
- P6: built train-ready package with quality gate.
- P7: added dry-run training scaffold.
- P8: added experiment loop scaffold.
- P9: expanded preference candidates to cover all 20 tasks.
- No real training or GRPO has been run yet.
