# GPU Smoke SFT Report - 2026-06-24

## Result

PASS.

## Purpose

This run validates the training pipeline only. It is not a meaningful model-quality training run.

## Environment

- GPU: NVIDIA RTX 3090
- torch: 2.12.1+cu130
- CUDA available: true
- CUDA_VISIBLE_DEVICES: 1

## Data

- sft_train: 80
- sft_eval: 20
- dpo_train: 135
- decision: SMOKE_READY

## Tiny SFT Smoke

- model: sshleifer/tiny-gpt2
- max_steps: 3
- output_dir: models/codeguide_sft_tiny_smoke
- checkpoint: models/codeguide_sft_tiny_smoke/checkpoint-3
- train_rows: 80
- eval_rows: 20

## Interpretation

This validates:
- HF-style data loading
- tokenization/map step
- Trainer startup
- loss computation
- backward/optimizer steps
- checkpoint saving

This does not validate final model quality and should not be reported as performance improvement.

## Remaining Note

The tiny-gpt2 smoke saved full model weights. A target LoRA/QLoRA smoke should be run separately to verify adapter saving.
