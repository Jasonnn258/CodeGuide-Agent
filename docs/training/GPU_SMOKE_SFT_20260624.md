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

## Qwen LoRA Smoke

- model: Qwen/Qwen2.5-Coder-7B-Instruct
- max_steps: 3
- config: configs/training/sft_qwen2_5_coder_lora.json
- log: logs/sft_qwen_lora_smoke_20260624_223433.log
- result: BLOCKED (network error during model download)

### Details

- Data loading: 80 train / 20 eval rows mapped successfully.
- Model download failed with `httpx.RemoteProtocolError`:
  HuggingFace peer closed connection during `snapshot_download`,
  received 2.5 GB of a 4.8 GB shard file.
- HuggingFace cache grew from ~31G to ~37G during the attempt,
  confirming the process was actively downloading.
- Training never reached GPU or first step.

### Root cause

Transient network error from HuggingFace CDN — not a code or
pipeline bug. A retry should succeed once connectivity is stable.

## Remaining Note

The tiny-gpt2 smoke saved full model weights. The Qwen LoRA smoke
needs a retry to verify adapter saving.
