# CodeGuide Mini-Repo-Debug P6 Training Package

This package normalizes Mini-Repo-Debug exports into train-ready SFT and preference JSONL files.
SFT records may come from successful model rollouts or from gold/reference patches used as supervised patch examples.

## Files

- `sft_train.jsonl`
- `sft_eval.jsonl`
- `preference_train.jsonl`
- `preference_eval.jsonl`
- `manifest.json`

## Counts

- SFT train: 48
- SFT eval: 12
- Preference train: 71
- Preference eval: 18
- Gold/reference SFT: 41
- Rollout SFT: 19

## Safety

Model-facing JSONL files exclude evaluator-only verifier rows, raw test output fields, and oracle patch actions.
Aggregate reward fields may include pass/fail summaries for offline filtering.

## Limitations

- The preference split is very small and should not be treated as sufficient for model training.
- The replay check is a lightweight patch inspection gate, not a full execution replay.
