#!/usr/bin/env bash
set -euo pipefail

echo "== git status =="
git status --short

echo "== compile =="
python -m py_compile codeguide_agent/testing/mini_repo_trajectory_fixture.py
python -m py_compile scripts/summarize_mini_repo_pipeline.py

echo "== test =="
make test

echo "== clean-check =="
make clean-check

echo "== latest commits =="
git log --oneline -8

echo "== tags =="
git tag --list | grep mini-repo-debug || true

echo "Release check passed."
