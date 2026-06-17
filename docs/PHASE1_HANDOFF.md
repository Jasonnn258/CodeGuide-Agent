# Phase 1 Handoff

## 1. Project Positioning

CodeGuide-Agent is a verifier-driven code repair agentic RL system. The main scenario is Auto Repair / repo-level debugging: given an issue, a mini repository, and public/hidden tests, an agent should inspect the repo, localize the bug, make a minimal patch, run verifiers, log the trajectory, and receive a programmatic reward.

Phase 1 is infrastructure only. Do not expand this project into IDE completion, VLM workflows, generic multi-agent systems, model training, or large-scale GRPO.

## 2. Current Phase 1 Implementation Summary

Implemented:

- Package scaffolding under `codeguide_agent/`.
- Mini-Repo-Debug dataset schema and validator.
- Five handcrafted pytest mini repo tasks under `data/mini_repo_debug/repos/`.
- `data/mini_repo_debug/tasks.jsonl`.
- Shared tool layer: `repo_tree`, `search_repo`, `read_file`, `edit_file`, `run_test`, `git_diff`, `rollback`.
- JSONL trajectory logger.
- Reward calculator v1.
- Deterministic prompt-only baseline with `noop` and direct `gold` simulation modes.
- Evaluation runner and metrics summary.
- Validation/eval scripts.
- README, Phase 1 notes, config, and Python packaging metadata.

## 3. Repository Structure Overview

- `codeguide_agent/dataset/`: task schema loading and dataset validation.
- `codeguide_agent/tools/`: structured local repo-debug tools.
- `codeguide_agent/trajectory/`: JSONL action-observation logging.
- `codeguide_agent/reward/`: reward v1 and simple reward-hacking checks.
- `codeguide_agent/baselines/`: deterministic prompt-only baseline.
- `codeguide_agent/eval/`: task discovery, evaluation loop, and aggregate metrics.
- `data/mini_repo_debug/repos/task_001` through `task_005`: handcrafted buggy mini repos.
- `data/mini_repo_debug/tasks.jsonl`: task index used by eval when present.
- `scripts/`: shell entry points for validation and Phase 1 eval.
- `configs/phase1.yaml`: default dataset root, eval mode, and timeout.
- `docs/`: Phase 1 notes and handoff material.

## 4. Key Commands

Validate the dataset:

```bash
python -m codeguide_agent.dataset.validate_mini_repo_task --root data/mini_repo_debug
bash scripts/validate_mini_repo_debug.sh
```

Run the no-op Phase 1 eval:

```bash
bash scripts/run_phase1_eval.sh
```

Run eval directly:

```bash
python -m codeguide_agent.eval.run_eval --root data/mini_repo_debug --mode noop
```

Check package syntax:

```bash
python -m compileall codeguide_agent
```

Check gold patches:

```bash
for d in data/mini_repo_debug/repos/task_*; do (cd "$d" && git apply --check gold.patch) || exit 1; done
```

## 5. Validation Results

Known current status:

- Dataset validator passes 5/5 tasks.
- `bash scripts/validate_mini_repo_debug.sh` passes.
- `bash scripts/run_phase1_eval.sh` exits 0 and prints a summary.
- `python -m compileall codeguide_agent` passes.
- All `gold.patch` files apply cleanly.
- No-op eval reports `public_pass_rate = 0.0` and `hidden_pass_rate = 0.0`, which is expected because the baseline makes no repair.

The current environment may not have `pytest` installed. `pyproject.toml` includes `pytest` in dev extras.

## 6. Known Limitations

- Baseline behavior is intentionally simple and deterministic.
- `--mode gold` may apply `gold.patch` directly inside the task repo.
- Evaluation does not yet run tasks in isolated temporary copies.
- Reward v1 is heuristic and shallow: pass/fail flags, changed file/line counts, test modification flag, hardcode suspicion flag, regression flag, and total reward.
- `git_diff` returns an empty diff for non-Git task repos.
- Tool checkpointing is simple and file-level; it is not a full repo snapshot.

## 7. Design Risks

- In-place gold simulation can mutate benchmark tasks and contaminate later runs.
- Non-Git mini repos limit diff fidelity unless eval or baseline creates isolated Git-backed workspaces.
- `run_test` uses `shell=True`; commands come from local metadata, but keep metadata trusted and reviewed.
- Hardcode suspicion is regex-based and can miss subtle reward hacking.
- The no-op baseline validates plumbing, not repair ability.
- Missing local `pytest` can make public/hidden verifier results misleading until dev dependencies are installed.

## 8. Files Reviewers Should Inspect First

- `AGENTS.md`
- `README.md`
- `docs/phase1.md`
- `configs/phase1.yaml`
- `data/mini_repo_debug/tasks.jsonl`
- `codeguide_agent/dataset/validate_mini_repo_task.py`
- `codeguide_agent/baselines/prompt_only.py`
- `codeguide_agent/eval/run_eval.py`
- `codeguide_agent/eval/metrics.py`
- `codeguide_agent/reward/calculator.py`
- `codeguide_agent/reward/hacking_checks.py`
- `codeguide_agent/tools/`
- `data/mini_repo_debug/repos/task_001/metadata.json`

## 9. Next Recommended Implementation Step

Implement isolated temp-copy evaluation for `--mode gold` and future repair agents. The evaluator should copy each task repo to a temporary workspace, apply or generate patches there, run public/hidden tests there, collect diffs/rewards/trajectories, and leave the canonical dataset untouched.

Do not implement this in-place until the isolation behavior is explicit and tested.

## 10. What Not To Implement Yet

- Model training.
- GRPO or rollout-group optimization.
- SFT data builders beyond basic trajectory JSONL.
- IDE completion.
- VLM or screenshot-based code understanding.
- Generic multi-agent orchestration.
- External paid API integrations.
- Dataset/task rewrites just to improve no-op scores.
