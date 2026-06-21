# Canonical Training Data Pipeline

This document defines the canonical training-data path for CodeGuide-Agent.

## Canonical entrypoints

1. Export SFT and preference candidates:

   python -m codeguide_agent.dataset.export_training_candidates --root data/mini_repo_debug --out data/mini_repo_debug/exports

2. Prepare train-ready package:

   python -m codeguide_agent.dataset.prepare_training_package --root data/mini_repo_debug --exports data/mini_repo_debug/exports --out data/mini_repo_debug/train_package

3. Expand preference bank:

   python -m codeguide_agent.dataset.expand_preference_candidates --root data/mini_repo_debug

4. Convert to HF-style training data:

   python -m codeguide_agent.training.build_hf_training_data --package data/mini_repo_debug/train_package --out data/mini_repo_debug/hf_training

5. Run SFT smoke or LoRA training:

   make train-sft-smoke
   make train-sft

## Source of truth

The source of truth for SFT candidates is:

- data/mini_repo_debug/exports/p5_sft_rollouts.jsonl

The source of truth for preference candidates is:

- data/mini_repo_debug/exports/p5_preference_pairs.jsonl
- data/mini_repo_debug/preference_bank/preference_candidates.jsonl

## Legacy builders

Older modules under codeguide_agent.data_builders or codeguide_agent.training_data are legacy compatibility utilities.
They should not be used as the public project entrypoint.

Do not introduce another independent SFT builder.

## Interview-safe explanation

Successful non-gold LLM trajectories are filtered and sanitized by export_training_candidates.py, written to p5_sft_rollouts.jsonl, packaged by prepare_training_package.py, and converted to HF-style training format by build_hf_training_data.py.
