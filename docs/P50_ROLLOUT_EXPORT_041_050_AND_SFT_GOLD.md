# P50-P54 Rollout Export 041-050 And Gold SFT

P50-P54 expands Mini-Repo-Debug from 40 to 50 active tasks and fixes the SFT growth bottleneck without running real training, external APIs, or the `llm` policy.

## SFT Bottleneck Fix

Before P50, SFT stayed at 19 records because only successful LLM rollout trajectories were exported as SFT candidates. Local deterministic policies are useful for preference mining, but they do not produce successful patch trajectories.

P50 adds a safe reference SFT path:

- `record_type`: `gold_patch_sft_candidate`
- `source`: `gold_patch`
- model-facing context: `issue.md` plus public test command
- supervised target: the task reference patch diff
- localization metadata: target files and gold functions

These records are marked as reference patch examples, not model-generated rollouts. They exclude hidden test content, hidden output, evaluator-only metadata payloads, and oracle actions.

## New Tasks

Added active tasks:

- `task_041`: parsing edge case
- `task_042`: path handling
- `task_043`: cache key
- `task_044`: optional/default args
- `task_045`: boundary condition
- `task_046`: string normalization
- `task_047`: dict mutation
- `task_048`: date boundary
- `task_049`: JSON config parsing
- `task_050`: CLI argument propagation

Seven of the ten tasks are hard-pair friendly: buggy code passes public tests but fails hidden tests. All ten reference patches apply cleanly and pass public plus hidden tests.

## Rollout Export

Script:

```bash
python scripts/p50_rollout_export_041_050.py
```

Policies:

- `noop`
- `heuristic`
- `scripted`

No `llm` policy, real training, or external API calls are used.

Outputs:

- `data/mini_repo_debug/rollouts/p50_041_050/noop.jsonl`
- `data/mini_repo_debug/rollouts/p50_041_050/heuristic.jsonl`
- `data/mini_repo_debug/rollouts/p50_041_050/scripted.jsonl`
- `data/mini_repo_debug/rollouts/p50_041_050/summary.json`
- refreshed `data/mini_repo_debug/exports/`
- refreshed `data/mini_repo_debug/preference_bank/`
- refreshed `data/mini_repo_debug/train_package/`
- refreshed `data/mini_repo_debug/hf_training/`

## Counts

P50 baseline:

- active tasks: 40
- planned backlog: 60
- target total: 100
- SFT: 19
- preference: 53
- hard preference: 11

After P50 rollout/export:

- active tasks: 50
- planned backlog: 50
- target total: 100
- SFT: 50
- preference: 69
- hard preference: 17

## Checks

Use:

```bash
make p50-check
```

The check verifies that `task_041-task_050` have local trajectories, the preference bank and package counts agree, and the train package includes gold/reference SFT records.

## Next Recommendation

Continue expanding deterministic task batches, preferably `task_051-task_060`, while keeping the local rollout/export loop bounded. Real training should wait until the dataset has broader task coverage and a larger validated preference set.
