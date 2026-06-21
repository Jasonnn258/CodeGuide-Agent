# P13 CI and Release Check

P13 adds a minimal CI gate for the Mini-Repo-Debug pipeline.

## GitHub Actions

Workflow file:

.github/workflows/mini_repo_debug_ci.yml

The CI runs on push to main and on pull requests.

It checks:

- key Python files compile;
- unit tests pass;
- clean-check passes without generated trajectories.

## Local release check

Run:

scripts/release_check.sh

This performs the same core checks locally before pushing tags or presenting the project.

## Why this matters

The project now has three reproducibility layers:

1. make test verifies the local unit test suite.
2. make clean-check verifies tests do not depend on generated trajectories.
3. GitHub Actions verifies the same checks on a clean remote runner.

This makes the Mini-Repo-Debug pipeline easier to review, reproduce, and discuss in interviews.
