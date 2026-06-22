# P55 Rollout Export 051-060

P55 expands Mini-Repo-Debug from 50 to 60 active tasks using bounded local rollout policies without running real training, external APIs, or the `llm` policy.

## New Tasks

Added active tasks:

- `task_051`: error handling — parse_int swallows TypeError
- `task_052`: numeric edge case — celsius_to_fahrenheit uses integer division
- `task_053`: sorting/filtering — sort_names is case-sensitive instead of case-insensitive
- `task_054`: service helper integration — build_pipeline only executes the first step
- `task_055`: case-insensitive handling — normalize_tag preserves surrounding whitespace
- `task_056`: multi-file integration — stats report crashes on empty input
- `task_057`: stateful side effect — HitCounter.reset leaves overflow flag set
- `task_058`: idempotency — ensure_dir is not idempotent
- `task_059`: validation logic — is_valid_username rejects whitespace-padded names
- `task_060`: config merge — merge_config overwrites nested dicts instead of deep-merging

All ten tasks are hard-pair friendly: buggy code passes public tests but fails hidden tests. All ten gold patches apply cleanly and pass public plus hidden tests.

## Repair and Verify

Script:

```bash
python scripts/p55_repair_and_verify_tasks_051_060.py
```

This script creates all ten task directories, writes the buggy source code, public tests, hidden tests, metadata, and regenerates each gold.patch from a clean git diff. It then verifies each task's expected buggy test shape and confirms that the gold patch resolves all failures.

## Rollout Export

Script:

```bash
python scripts/p55_rollout_export_051_060.py
```

Policies:

- `noop`
- `heuristic`
- `scripted`

No `llm` policy, real training, or external API calls are used.

Outputs:

- `data/mini_repo_debug/rollouts/p55_051_060/noop.jsonl`
- `data/mini_repo_debug/rollouts/p55_051_060/heuristic.jsonl`
- `data/mini_repo_debug/rollouts/p55_051_060/scripted.jsonl`
- `data/mini_repo_debug/rollouts/p55_051_060/summary.json`
- refreshed `data/mini_repo_debug/exports/`
- refreshed `data/mini_repo_debug/preference_bank/`
- refreshed `data/mini_repo_debug/train_package/`
- refreshed `data/mini_repo_debug/hf_training/`

## Canonical Export / Package Steps

The rollout script runs the canonical pipeline steps:

- `codeguide_agent.dataset.export_training_candidates`
- `codeguide_agent.dataset.expand_preference_candidates`
- `codeguide_agent.dataset.prepare_training_package`
- `codeguide_agent.training.build_hf_training_data`

## Counts

P55 baseline:

- active tasks: 50
- planned backlog: 50
- target total: 100
- SFT: 50
- preference: 69
- hard preference: 17

After P55 rollout/export:

- active tasks: 60
- planned backlog: 40
- target total: 100
- SFT: 60 (10 new gold_patch_sft_candidate records)
- preference: >69 (new preference pairs from 10 tasks x 3 policies)
- hard preference: >17 (all 10 tasks are hard-pair)

## Checks

Use:

```bash
make p55-check
```

The check verifies that `task_051-task_060` have local trajectories, the preference bank and package counts agree, and the train package includes gold/reference SFT records.

## Next Recommendation

Continue expanding with `task_061-task_070` (P60+) to reach closer to the 100-task target. Real training should wait until the dataset has broader task coverage and a validated preference set crossing the 100-record threshold.
