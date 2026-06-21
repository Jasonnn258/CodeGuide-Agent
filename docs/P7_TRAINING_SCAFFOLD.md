# P7 Training Scaffold

P7 adds an offline training scaffold for the P6 Mini-Repo-Debug package. It does not train a model, download a model, require a GPU, or call paid APIs.

## Data Package

Build or refresh the package:

```bash
python -m codeguide_agent.dataset.export_training_candidates --root data/mini_repo_debug --out data/mini_repo_debug/exports
python -m codeguide_agent.dataset.prepare_training_package --root data/mini_repo_debug --out data/mini_repo_debug/train_package
```

## Dry Runs

SFT dry run:

```bash
python -m codeguide_agent.training.dry_run_train --package data/mini_repo_debug/train_package --mode sft
```

Preference dry run:

```bash
python -m codeguide_agent.training.dry_run_train --package data/mini_repo_debug/train_package --mode preference
```

Each dry run validates the package, checks sanitization, batches examples, writes a formatted preview, and creates `dry_run_summary.json`.

## Replay Scaffold

The replay scaffold inspects exported final patches referenced by a dry-run directory:

```bash
python -m codeguide_agent.training.replay_eval --run-dir data/mini_repo_debug/train_package/dry_runs/sft
```

This is a lightweight offline patch inspection step. Hidden tests remain evaluator-only and are not executed by the training scaffold.

## Future Training Plug-In

Future SFT or DPO trainers should consume the same loader in `codeguide_agent.training.data`, then replace the dry-run batching step with framework-specific model/tokenizer code. The quality gate should remain mandatory before any real training job starts.

The current preference data has only one pair, so it is suitable for pipeline validation but too small for real preference training.
