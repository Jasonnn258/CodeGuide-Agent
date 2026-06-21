#!/usr/bin/env bash
set -euo pipefail

FORBIDDEN=(
  "tests_hidden"
  "metadata.json"
  "gold.patch"
  "apply_gold_patch"
  "\"stdout\""
  "\"stderr\""
  "SECRET_HIDDEN"
)

TARGETS=(
  "data/mini_repo_debug/exports"
  "data/mini_repo_debug/train_package"
  "data/mini_repo_debug/preference_bank"
  "experiments/mini_repo_debug"
)

echo "== model-facing artifact leakage audit =="

FAILED=0

for target in "${TARGETS[@]}"; do
  if [ ! -e "$target" ]; then
    continue
  fi

  for term in "${FORBIDDEN[@]}"; do
    if grep -R --line-number --fixed-strings "$term" "$target" 2>/dev/null; then
      echo "FORBIDDEN term found: $term in $target"
      FAILED=1
    fi
  done
done

if [ "$FAILED" -ne 0 ]; then
  echo "Leakage audit failed."
  exit 1
fi

echo "PASS: no forbidden terms found in model-facing artifacts."
