# P15 Model-Facing Artifact Leakage Audit

P15 adds a local and CI-backed audit for model-facing artifacts.

Command:

make audit

The audit scans generated model-facing artifacts for forbidden terms:

- tests_hidden
- metadata.json
- gold.patch
- apply_gold_patch
- raw stdout key
- raw stderr key
- SECRET_HIDDEN

Targets:

- data/mini_repo_debug/exports
- data/mini_repo_debug/train_package
- data/mini_repo_debug/preference_bank
- experiments/mini_repo_debug

The audit is also included in scripts/release_check.sh and GitHub Actions CI.

Why this matters:

Training candidates and preference data must not expose verifier-only hidden tests, oracle metadata paths, gold patch paths, or raw test outputs. Otherwise the dataset would leak evaluation information and make training or evaluation unreliable.
