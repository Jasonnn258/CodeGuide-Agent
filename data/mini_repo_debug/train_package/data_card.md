# CodeGuide Mini-Repo-Debug P6 Training Package

This package normalizes P5 Mini-Repo-Debug trajectory exports into train-ready SFT and preference JSONL files.

## Files

- `sft_train.jsonl`
- `sft_eval.jsonl`
- `preference_train.jsonl`
- `preference_eval.jsonl`
- `manifest.json`

## Counts

- SFT train: 16
- SFT eval: 3
- Preference train: 24
- Preference eval: 6

## Safety

Model-facing JSONL files exclude evaluator-only verifier rows, raw test output fields, and oracle patch actions.
Aggregate reward fields may include pass/fail summaries for offline filtering.

## Limitations

- The preference split is very small and should not be treated as sufficient for model training.
- The replay check is a lightweight patch inspection gate, not a full execution replay.
