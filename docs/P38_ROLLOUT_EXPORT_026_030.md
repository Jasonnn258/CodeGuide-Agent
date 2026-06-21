# P38 Rollout Export for task_026-task_030

P38 adds five active Mini-Repo-Debug tasks and a bounded local rollout/export loop. It does not run real training, the `llm` policy, or external APIs.

## Tasks

- `task_026`: `json_config_parsing`
- `task_027`: `cli_argument_propagation`
- `task_028`: `sorting_filtering`
- `task_029`: `error_handling`
- `task_030`: `multi_file_integration`

`task_026` and `task_028` are hard-pair friendly: the buggy implementation passes public tests and fails hidden tests.

## Verification

```bash
python scripts/p38_repair_and_verify_tasks_026_030.py
```

The verifier writes/repairs the task files, regenerates `gold.patch` from a temp git repo, checks that each patch applies, verifies the expected buggy public/hidden shape, and confirms the gold patch passes public plus hidden tests.

## Rollout and Export

```bash
python scripts/p38_rollout_export_026_030.py
```

The runner uses only deterministic local policies:

- `noop`
- `heuristic`
- `scripted`

Compact rollout summaries are written under:

- `data/mini_repo_debug/rollouts/p38_026_030/`

Canonical trajectories are written under:

- `data/mini_repo_debug/trajectories/`

After rollout, the script runs the canonical export/package path:

- `codeguide_agent.dataset.export_training_candidates`
- `codeguide_agent.dataset.expand_preference_candidates`
- `codeguide_agent.dataset.prepare_training_package` with the expanded preference bank
- `codeguide_agent.training.build_hf_training_data`

## Check

```bash
make p38-check
```

The check verifies that the five P38 tasks have trajectories, that the preference bank covers them, and that package preference counts match the expanded bank.

## Expected Count Direction

Active tasks should become `30`, planned backlog should become `70`, and target total should remain `100`. Preference data should increase beyond `30` and hard preference should remain at least `3`. SFT may remain `19` because no patch-capable LLM rollout is run in this phase.

## Observed P38 Counts

After running `python scripts/p38_rollout_export_026_030.py`:

- Active tasks: `25 -> 30`
- Planned backlog: `75 -> 70`
- Target total: `100`
- SFT total: `19 -> 19`
- Preference total: `30 -> 37`
- Preference bank total: `30 -> 37`
- Hard preference total: `3 -> 5`
- Rollout results: `15`
- Rollout failures: `0`

The increase came from preference candidates, not from new SFT records.

## Next Step

After P38 succeeds, continue expanding `task_031-task_035` or improve deterministic weak policies. Real training is still premature until SFT and preference counts are substantially larger.
