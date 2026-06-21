# P23-P30 Training Execution Pack

This pack makes CodeGuide-Agent directly runnable for smoke SFT training.

What is included:

- HF-style SFT and DPO data conversion.
- LoRA SFT training script based on Transformers Trainer and PEFT.
- DPO data readiness scaffold.
- Training preflight checks.
- Makefile training targets.
- Training configs for Qwen2.5-Coder LoRA and tiny smoke runs.

Important distinction:

Current data is enough for a smoke SFT run.
Current data is not enough for a meaningful final training claim.

Current data scale:

- SFT: 19 records.
- Preference: 23 records.
- Hard preference: 1 record.

Recommended real training threshold:

- At least 150 SFT records.
- At least 100 preference records.
- At least 30 hard public-pass-hidden-fail preference records.

Main commands:

make training-data
make training-preflight
make train-sft

For a tiny smoke run:

make train-sft-smoke

For a real Qwen2.5-Coder LoRA run on a GPU machine:

pip install -r requirements-training.txt
make training-data
MODEL_NAME=Qwen/Qwen2.5-Coder-7B-Instruct make train-sft

The output adapter is saved under models/codeguide_sft_qwen2_5_coder_lora by default.
