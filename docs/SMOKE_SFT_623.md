# Smoke SFT Report 623

This is a pipeline smoke test, not meaningful model training.

## Result

- preflight decision: SMOKE_READY
- CUDA available: true
- GPU: NVIDIA GeForce RTX 3090
- SFT train/eval: 80 / 20
- DPO train: 135
- model: sshleifer/tiny-gpt2
- max_steps: 3
- output_dir: models/codeguide_sft_tiny_smoke
- result: completed successfully

## Boundary

Do not claim model capability improvement. This only verifies HF data -> Trainer -> loss -> save path.
