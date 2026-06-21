# P11 Reproducible Runbook

This document records the stable offline reproduction entrypoints for the Mini-Repo-Debug pipeline.

## Scope

P11 does not run real model training, paid APIs, GRPO, or online evaluation. It packages the existing P4-P10/P10.1 pipeline into stable local commands.

## Main commands

make test
Runs the full lightweight unit test suite.

make clean-check
Temporarily removes data/mini_repo_debug/trajectories and verifies tests still pass.

make validate-pipeline
Runs the full offline Mini-Repo-Debug pipeline validation script.

make clean-generated
Removes generated reports, dry-run outputs, smoke experiment outputs, and Python caches.

## Current stable milestone

- 20 Mini-Repo-Debug tasks.
- Real DeepSeek baseline collected locally.
- P5 export: 19 SFT candidates plus 1 preference pair.
- P9 preference bank with full task coverage.
- P6 train-ready package with quality gate.
- P7 dry-run trainer and replay scaffold.
- P8 experiment loop scaffold.
- P10 full offline validation script and summary snapshot.
- P10.1 unit tests decoupled from generated trajectories.

## Non-goals

- No real SFT training.
- No preference training.
- No GRPO or RL.
- No paid API calls.
- No hidden tests exposed to model-facing exports.
