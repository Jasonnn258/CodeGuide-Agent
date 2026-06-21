#!/usr/bin/env bash
set -euo pipefail

rm -rf data/mini_repo_debug/reports
rm -rf data/mini_repo_debug/train_package/dry_runs
rm -rf experiments/mini_repo_debug/p10_pipeline_smoke
rm -rf experiments/mini_repo_debug/p8_sft_smoke

find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "Cleaned Mini-Repo-Debug generated artifacts."
echo "Note: data/mini_repo_debug/trajectories is intentionally preserved."
