# P42 Rollout Export for task_031-task_040

P42 adds ten active Mini-Repo-Debug tasks and a bounded local rollout/export loop. It does not run real training, the `llm` policy, or external APIs.

## Tasks

- `task_031`: `error_handling`
- `task_032`: `numeric_edge_case`
- `task_033`: `sorting_filtering`
- `task_034`: `service_helper_integration`
- `task_035`: `case_insensitive_handling`
- `task_036`: `multi_file_integration`
- `task_037`: `stateful_side_effect`
- `task_038`: `idempotency`
- `task_039`: `validation_logic`
- `task_040`: `config_merge`

Hard-pair-friendly tasks in this batch are `task_031`, `task_033`, `task_035`, `task_038`, `task_039`, and `task_040`: the buggy implementation passes public tests and fails hidden tests.

## Verification

```bash
python scripts/p42_repair_and_verify_tasks_031_040.py
```

The verifier writes/repairs the task files, regenerates `gold.patch` from a temp git repo, checks that each patch applies, verifies the expected buggy public/hidden shape, and confirms the gold patch passes public plus hidden tests.

## Rollout and Export

```bash
python scripts/p42_rollout_export_031_040.py
```

The runner uses only deterministic local policies:

- `noop`
- `heuristic`
- `scripted`

Compact rollout summaries are written under:

- `data/mini_repo_debug/rollouts/p42_031_040/`

Canonical trajectories are written under:

- `data/mini_repo_debug/trajectories/`

After rollout, the script runs the canonical export/package path:

- `codeguide_agent.dataset.export_training_candidates`
- `codeguide_agent.dataset.expand_preference_candidates`
- `codeguide_agent.dataset.prepare_training_package` with the expanded preference bank
- `codeguide_agent.training.build_hf_training_data`

## Check

```bash
make p42-check
```

The check verifies that the ten P42 tasks have trajectories, that the preference bank covers them, and that package preference counts match the expanded bank.

## Expected Count Direction

Active tasks should become `40`, planned backlog should become `60`, and target total should remain `100`. Preference data should increase beyond `37`, and hard preference should increase beyond `5` if the hard-pair tasks are exported correctly. SFT may remain `19` because no patch-capable LLM rollout is run in this phase.

## Observed P42 Counts

After running `python scripts/p42_rollout_export_031_040.py`:

- Active tasks: `30 -> 40`
- Planned backlog: `70 -> 60`
- Target total: `100`
- SFT total: `19 -> 19`
- Preference total: `37 -> 53`
- Preference bank total: `37 -> 53`
- Hard preference total: `5 -> 11`
- Rollout results: `30`
- Rollout failures: `0`

The increase came from preference candidates, not from new SFT records.

## Next Step

After P42 succeeds, continue task expansion or improve deterministic weak policies. Real training is still premature until SFT and preference counts are substantially larger.
