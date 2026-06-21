# P34 Rollout Export for task_021-task_025

P34 adds a bounded local rollout/export loop for the five active P32 tasks. It is designed to increase training-data coverage without running external LLM APIs or real training.

## Policies

The runner uses local deterministic policies only:

- `noop`
- `heuristic`
- `scripted`

`gold` is not run by default. Gold patches are used only as offline chosen/reference fixes by the preference-bank exporter.

## Command

```bash
python scripts/p34_rollout_export_021_025.py
```

The script runs rollouts only for:

- `task_021`
- `task_022`
- `task_023`
- `task_024`
- `task_025`

It writes compact rollout outputs under:

- `data/mini_repo_debug/rollouts/p34_021_025/`

Canonical trajectories are written under:

- `data/mini_repo_debug/trajectories/`

After rollout, it runs the canonical export/package steps:

- `codeguide_agent.dataset.export_training_candidates`
- `codeguide_agent.dataset.expand_preference_candidates`
- `codeguide_agent.dataset.prepare_training_package` with the expanded preference bank
- `codeguide_agent.training.build_hf_training_data`

## Checks

```bash
make p34-check
```

The check verifies that the five P34 tasks have trajectories, that the preference bank covers them, and that train-package preference counts match the expanded bank.

## Expected Count Direction

SFT is not expected to increase because P34 does not run an LLM patching policy. Preference counts should increase because the five new tasks can now contribute original-buggy/no-patch and local-policy rejected candidates against gold/reference fixes.

Hard preference may increase when a deterministic rejected trajectory passes public tests but fails hidden tests. Hidden verifier details remain evaluator-only and are not exported as model-facing content.

## Observed P34 Counts

After running `python scripts/p34_rollout_export_021_025.py`:

- SFT total: `19 -> 19`
- Preference total: `23 -> 30`
- Preference bank total: `23 -> 30`
- Hard preference total: `1 -> 3`
- Rollout results: `15`
- Rollout failures: `0`

The increase came from preference candidates, not from new SFT records.

## Next Step

After P34 succeeds, the recommended next step is to continue task expansion to `task_026-task_030` or improve local/weak rollout policies. Real training is still premature until SFT and preference counts are much larger.
