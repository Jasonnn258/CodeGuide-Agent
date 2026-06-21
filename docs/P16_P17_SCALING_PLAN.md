# P16/P17 Scaling Plan

## Goal

Move Mini-Repo-Debug from a 20-task engineering prototype to a training-ready benchmark and data pipeline.

P16 focuses on task expansion.
P17 focuses on rollout expansion, preference diversity, and training-readiness gates.

## Current baseline

Current stable state:

- 20 Mini-Repo-Debug tasks.
- Real DeepSeek baseline collected.
- P5 export: 19 SFT candidates plus 1 hard preference pair.
- P9 preference bank: 23 preference candidates with 20-task coverage.
- Train package, quality gate, dry-run trainer, replay eval, experiment scaffold, Makefile, clean-check, CI, and leakage audit are in place.

Current limitation:

- Dataset is structurally ready but statistically small.
- Preference data is dominated by original-buggy-vs-gold pairs.
- Only one real public-pass-hidden-fail LLM preference pair exists.
- No real SFT or preference training should be claimed yet.

## P16: Task expansion target

Target scale:

- V1: 50 tasks.
- V2: 100 tasks.
- V3: 200 tasks if training signal is still sparse.

Recommended distribution for 100 tasks:

- 15 parsing and string normalization tasks.
- 10 mutable/default argument and state mutation tasks.
- 10 boundary condition tasks.
- 10 path/file handling tasks.
- 10 CLI/config propagation tasks.
- 10 error handling and exception semantics tasks.
- 10 sorting/filtering/ranking tasks.
- 10 cache/key/idempotency tasks.
- 10 date/time/numeric edge cases.
- 5 multi-file integration tasks.

Difficulty distribution:

- 50 easy tasks: one-file localized patch, obvious public signal.
- 35 medium tasks: one or two files, public tests under-specify hidden edge.
- 15 hard tasks: multi-file or semantic edge case, likely public-pass-hidden-fail.

Each task must include:

- issue.md.
- public tests.
- hidden tests.
- metadata.json.
- gold.patch.
- original buggy repo state.
- deterministic validation.
- no network dependency.
- no nondeterministic clock unless frozen in tests.

## P16 task design principles

A good task should create a realistic public-hidden generalization gap.

Good hidden-fail patterns:

- Public checks the common case, hidden checks aliasing or mutation.
- Public checks normal input, hidden checks empty input or boundary input.
- Public checks Unix path, hidden checks nested or absolute path behavior.
- Public checks single item, hidden checks duplicates or ordering.
- Public checks one config field, hidden checks propagation across helper functions.
- Public checks happy path, hidden checks explicit exception behavior.

Bad tasks:

- Pure typo fixes with no generalization dimension.
- Tasks where gold patch can be guessed from hidden test names.
- Tasks requiring external services.
- Tasks requiring large dependencies.
- Tasks whose public and hidden tests are basically identical.
- Tasks that leak answer through metadata or issue wording.

## P17: Rollout and preference expansion

Target rollout collection:

- At least 3 policies per task:
  - prompt-only baseline.
  - current LLM baseline.
  - stronger LLM baseline if budget allows.
- At least 100 tasks x 3 policies = 300 trajectories.
- Prefer high-concurrency collection with strict rate and budget controls.
- Save every trajectory with action trace, final patch, public result, hidden result, and diagnostics.

Target training data:

- SFT candidates: at least 150 successful trajectories.
- Preference candidates: at least 100 meaningful pairs.
- Hard preference pairs: at least 30 public-pass-hidden-fail cases.
- Rejected sources should include:
  - no_patch.
  - invalid_action.
  - public_fail.
  - syntax_error.
  - public_pass_hidden_fail.
  - too_narrow_patch.
  - wrong_file_patch.
  - overbroad_patch.

Preference quality hierarchy:

1. Best: public-pass-hidden-fail LLM patch vs gold patch.
2. Good: public-fail LLM patch vs gold patch.
3. Useful for scaffold: original buggy/no patch vs gold patch.
4. Lower value: synthetic rejected patch if clearly labeled.

## Training readiness gate

Do not start real training until all conditions pass:

- task_count >= 100.
- sft_total >= 150.
- preference_total >= 100.
- hard_preference_total >= 30.
- leakage_audit_passed = true.
- clean_check_passed = true.
- train_package_quality_gate_passed = true.
- no hidden tests or gold paths in model-facing files.
- eval split contains tasks unseen in training data.
- preference records have diverse rejection reasons.

## Real training sequence

Stage 1: SFT smoke

- Use a small model or LoRA adapter.
- Train on SFT candidates only.
- Goal is format/tool-use stability, not final benchmark claims.
- Compare against prompt-only baseline.

Stage 2: Preference training smoke

- Use preference pairs after SFT.
- Start with DPO-style training before online RL.
- Goal is reducing public-pass-hidden-fail behavior.

Stage 3: Agentic RL candidate

- Only after enough tasks and stable evaluator.
- Rollouts must be on-policy.
- Reward should include public pass, hidden pass, patch sanity, leakage penalty, and invalid action penalty.
- Avoid claiming RL before preference data and evaluator are stable.

## Reporting metrics

Core metrics:

- public_pass_rate.
- hidden_pass_rate.
- public_pass_hidden_fail_rate.
- syntax_error_rate.
- invalid_action_rate.
- leakage_rate.
- patch_inspection_pass_rate.
- task coverage.
- preference rejection reason distribution.

Important ablations:

- prompt-only baseline.
- SFT only.
- SFT plus preference.
- stronger prompt baseline.
- training data without hard preference pairs.

## P16/P17 deliverables

P16 deliverables:

- docs/P16_P17_SCALING_PLAN.md.
- docs/TASK_EXPANSION_SPEC.md.
- data/mini_repo_debug/task_backlog.json.
- scripts/report_dataset_scale.py.

P17 deliverables:

- rollout collection plan.
- preference diversity report.
- training readiness report.
- final decision: ready or not ready for real training.
