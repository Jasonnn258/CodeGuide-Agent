#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-data/mini_repo_debug}"
SNAPSHOT_DIR="${2:-docs/snapshots}"
EXP_NAME="${3:-p10_pipeline_smoke}"
EXP_DIR="experiments/mini_repo_debug/${EXP_NAME}"

mkdir -p "$SNAPSHOT_DIR"

echo "== 1. Unit tests =="
python -m codeguide_agent.testing.simple_pytest tests -q

echo "== 2. Dataset validation =="
python -m codeguide_agent.dataset.validate_mini_repo_task --root "$ROOT"
bash scripts/validate_mini_repo_debug.sh

echo "== 3. Compile =="
python -m compileall codeguide_agent

echo "== 4. Leakage audit =="
python -m codeguide_agent.dataset.audit_leakage --root "$ROOT"

echo "== 5. Rebuild preference bank =="
python -m codeguide_agent.dataset.expand_preference_candidates \
  --root "$ROOT" \
  --out "$ROOT/preference_bank"

echo "== 6. Rebuild P5 exports =="
python -m codeguide_agent.dataset.export_training_candidates \
  --root "$ROOT" \
  --out "$ROOT/exports"

echo "== 7. Rebuild train package =="
python -m codeguide_agent.dataset.prepare_training_package \
  --root "$ROOT" \
  --out "$ROOT/train_package" \
  --preference-bank "$ROOT/preference_bank/preference_candidates.jsonl"

echo "== 8. Dry-run training =="
python -m codeguide_agent.training.dry_run_train \
  --package "$ROOT/train_package" \
  --mode sft

python -m codeguide_agent.training.dry_run_train \
  --package "$ROOT/train_package" \
  --mode preference

echo "== 9. Experiment smoke =="
rm -rf "$EXP_DIR"

python -m codeguide_agent.training.create_experiment \
  --package "$ROOT/train_package" \
  --mode sft \
  --run-name "$EXP_NAME"

python -m codeguide_agent.training.mock_train_artifact \
  --run-dir "$EXP_DIR"

if python -m codeguide_agent.training.eval_experiment --run-dir "$EXP_DIR"; then
  echo "eval_experiment passed"
else
  echo "eval_experiment failed or CLI args differ; trying replay_eval fallback"
  python -m codeguide_agent.training.replay_eval --run-dir "$EXP_DIR"
fi

echo "== 10. Generate summary =="
python scripts/summarize_mini_repo_pipeline.py \
  --root "$ROOT" \
  --experiment "$EXP_DIR" \
  --out "$SNAPSHOT_DIR/mini_repo_debug_p4_p10_summary.md"

echo "== DONE =="
echo "Summary: $SNAPSHOT_DIR/mini_repo_debug_p4_p10_summary.md"
