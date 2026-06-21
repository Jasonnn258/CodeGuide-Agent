# P8 Experiment Loop

P8 adds a minimal experiment registry and trained-policy scaffold for Mini-Repo-Debug. It does not train a model, download weights, use a GPU, or call paid APIs.

## Flow

1. Prepare the P6 package:

```bash
python -m codeguide_agent.dataset.prepare_training_package --root data/mini_repo_debug --out data/mini_repo_debug/train_package
```

2. Create an experiment:

```bash
python -m codeguide_agent.training.create_experiment --package data/mini_repo_debug/train_package --mode sft --run-name p8_sft_smoke
```

This creates:

- `experiments/mini_repo_debug/<run_name>/config.json`
- `experiments/mini_repo_debug/<run_name>/metrics.json`
- `experiments/mini_repo_debug/<run_name>/artifacts.json`
- `experiments/mini_repo_debug/<run_name>/replay_report.json`
- `experiments/mini_repo_debug/<run_name>/eval_summary.json`

The registry records the package hash, package counts, selected mode, git commit when available, and sanitization status.

3. Attach a mock artifact:

```bash
python -m codeguide_agent.training.mock_train_artifact --run-dir experiments/mini_repo_debug/p8_sft_smoke
```

The mock artifact is deterministic metadata only. It stores patch candidates from the train package and explicitly records that it contains no model weights.

4. Run replay-style evaluation:

```bash
python -m codeguide_agent.training.eval_experiment --run-dir experiments/mini_repo_debug/p8_sft_smoke --root data/mini_repo_debug --limit 20
```

The replay check inspects exported patch candidates against task repositories. It does not run verifier-only tests or expose verifier-only content to a policy.

## Future Real Training

Real SFT or DPO training can later replace the mock artifact by writing compatible metadata under the same run directory and registering adapter paths in `artifacts.json`. The trained policy interface can then load those artifacts and produce patch candidates for the same replay/evaluation path.

The current preference package has only one pair, so it is useful for schema and integration checks, not for meaningful preference training.

## Safety Boundary

P8 preserves the P6/P7 sanitization gate before any training or artifact step reads package records. Model-facing records exclude verifier-only file paths, raw verifier stdout/stderr, and oracle patch actions. Aggregate reward summaries may be used for offline filtering and manifests, but verifier content remains outside prompts and policy inputs.
