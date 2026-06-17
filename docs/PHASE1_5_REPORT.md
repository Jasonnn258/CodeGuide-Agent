# Phase 1.5 Validation Report

## 1. Phase 1.5 Goal

Phase 1.5 hardens the Phase 1 Mini-Repo-Debug infrastructure into a safe, non-destructive, reproducible evaluation system for verifier-driven code repair. Evaluation must run in isolated temporary workspaces, apply gold patches only to temp copies, verify original repos are unchanged, and expose reward-hacking and invalid-action signals without implementing training or GRPO.

## 2. Environment and Dependency Status

Initial dependency check:

```text
pytest_available= False
```

`pip install -e ".[dev]"` was attempted. The first sandboxed attempt failed because PyPI DNS/network access was blocked while installing build dependencies. The command was rerun with approved network access and completed successfully:

```text
Successfully installed codeguide-agent-0.1.0 iniconfig-2.3.0 pytest-9.1.0
```

Final dependency check:

```text
pytest_available= True
```

## 3. What Was Implemented Before This Validation

- Phase 1 package scaffolding, dataset validator, tool layer, trajectory logger, reward v1, baseline runner, eval runner, scripts, config, and docs.
- Phase 1.5 isolated evaluation in `codeguide_agent/eval/run_eval.py`.
- Temp-copy evaluation rooted at `/tmp/codeguide_eval` by default.
- Gold patch application only inside temp task copies.
- Original repo checksum verification before and after eval.
- CLI flags: `--mode noop|gold`, `--task-id`, `--run-hidden`, `--temp-root`, `--keep-temp`.
- Explicit pytest preflight failure message: `pip install -e .[dev]`.
- Programmatic hardcode checks, unrelated edit detection, invalid-action reward penalty, and citation verifier skeleton.

## 4. Validation Commands Run

Dependency checks and installation:

```bash
python - <<'PY'
import importlib.util
print("pytest_available=", importlib.util.find_spec("pytest") is not None)
PY
pip install -e ".[dev]"
```

Validation:

```bash
python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
bash scripts/validate_mini_repo_debug.sh
python -m compileall codeguide_agent
```

Evaluation:

```bash
python -m codeguide_agent.eval.run_eval --root data/mini_repo_debug --mode noop --temp-root /tmp/codeguide_eval
python -m codeguide_agent.eval.run_eval --root data/mini_repo_debug --mode gold --temp-root /tmp/codeguide_eval
python -m codeguide_agent.eval.run_eval --root data/mini_repo_debug --mode gold --run-hidden --temp-root /tmp/codeguide_eval
bash scripts/run_phase1_eval.sh
```

Safety smoke check:

```bash
python - <<'PY'
from codeguide_agent.eval.run_eval import compute_repo_checksum, discover_tasks, evaluate_task
...
PY
```

## 5. Eval Results

No-op eval:

```text
num_tasks: 5
public_pass_rate: 0.0
hidden_pass_rate: 0.0
average_changed_files: 0.0
average_changed_lines: 0.0
test_file_modified_rate: 0.0
hardcode_flag_rate: 0.0
average_tool_calls: 7.0
```

Gold eval, public tests only:

```text
num_tasks: 5
public_pass_rate: 1.0
hidden_pass_rate: 0.0
average_changed_files: 1.0
average_changed_lines: 6.4
test_file_modified_rate: 0.0
hardcode_flag_rate: 0.0
average_tool_calls: 7.0
```

Gold eval with hidden tests:

```text
num_tasks: 5
public_pass_rate: 1.0
hidden_pass_rate: 1.0
average_changed_files: 1.0
average_changed_lines: 6.4
test_file_modified_rate: 0.0
hardcode_flag_rate: 0.0
average_tool_calls: 7.0
```

`bash scripts/run_phase1_eval.sh` completed successfully and ran isolated no-op plus isolated public-only gold eval. It does not run hidden tests unless `RUN_HIDDEN=1` is set.

## 6. Original Repo Mutation Check

An explicit checksum safety run executed gold mode with hidden tests in a separate temp root and compared every original task repo before and after evaluation.

```text
all_original_repos_unchanged= True
per_task_unchanged= {'task_001': True, 'task_002': True, 'task_003': True, 'task_004': True, 'task_005': True}
all_result_flags_unchanged= True
```

Original task repos stayed unchanged. Gold eval did not mutate canonical repos. Test files were not modified.

## 7. Reward / Hacking Checks Status

Observed in the gold hidden safety run:

```text
test_file_modified_flags= [False, False, False, False, False]
hardcode_flags= [False, False, False, False, False]
changed_files_counts= [1, 1, 1, 1, 1]
changed_lines_counts= [20, 2, 4, 4, 2]
```

Reward output reports changed file counts, changed line counts, test modification flags, hardcode flags, unrelated edit fields, invalid action counts, and total reward. Citation verification exists as a skeleton and checks citation format, file existence, line existence, and whether the cited file was opened or appeared in test logs.

## 8. Known Limitations

- No training, GRPO, IDE completion, VLM, or generic multi-agent behavior is implemented.
- Baseline remains deterministic and simple: no-op or gold-patch simulation.
- `scripts/run_phase1_eval.sh` runs hidden tests only when `RUN_HIDDEN=1`.
- Hardcode detection is heuristic and programmatic, not a complete semantic detector.
- Unrelated edit detection depends on `gold_files` and any future `suspicious_files`.
- Citation verification is a skeleton; future rollout logic must pass opened-file and test-log evidence.
- Evaluation writes trajectory logs by default; validation artifacts were removed after this report run.

## 9. Next Recommended Step

Implement a minimal rollout interface skeleton that can consume structured actions and produce trajectory records without adding training or GRPO. It should expose invalid JSON, unknown tool, timeout, duplicate tool call, opened-file, suspicious-file, and citation evidence signals to the existing reward calculator.

Phase 2A update: this rollout skeleton and a trajectory-to-SFT data builder have now been implemented. The system remains local and deterministic, with no training or GRPO added.

## 10. Files Reviewers Should Inspect

- `codeguide_agent/eval/run_eval.py`
- `codeguide_agent/baselines/prompt_only.py`
- `codeguide_agent/reward/calculator.py`
- `codeguide_agent/reward/hacking_checks.py`
- `scripts/run_phase1_eval.sh`
- `data/mini_repo_debug/tasks.jsonl`
- `docs/PHASE1_HANDOFF.md`
- `README.md`
- `pyproject.toml`
