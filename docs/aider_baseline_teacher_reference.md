# Aider as Baseline, Teacher, and Reference

This note is adapted from the local markdown file
`/Users/yjx/Code/Aider在CodeGuide-Agent中的定位.md`.

## Positioning

Aider should not be the main CodeGuide-Agent engineering base. It is a mature
terminal AI pair-programming product, while CodeGuide-Agent is a research
platform for repo-level debugging, evaluation, reward modeling, trajectory
mining, and training-data construction.

In CodeGuide-Agent, Aider has three roles:

- Strong baseline for Mini-Repo-Debug tasks.
- Teacher/data generator after verifier filtering.
- Repo-map and edit-format design reference.

CodeGuide-Agent keeps a forge-style runtime package as a baseline/demo runtime
and reference for event logs, tool execution, and research trajectories. The
canonical Mini-Repo-Debug rollout path is `RolloutCollector` plus
`codeguide_agent/tools/*`.

## Why Not Directly Fork Aider?

Aider is strong at terminal coding workflows, multi-model support, git
integration, lint/test repair, repo maps, and edit formats. Those are valuable,
but the research contribution of CodeGuide-Agent is elsewhere:

- dataset design,
- public/hidden verifier evaluation,
- gold file/function localization,
- patch minimality checks,
- no-hardcode and no-test-deletion checks,
- process reward,
- SFT/DPO/GRPO data construction,
- model weakness analysis.

Directly making CodeGuide-Agent a thin Aider wrapper would weaken that research
story.

## Strong Baseline

Run Aider on the same Mini-Repo-Debug tasks as CodeGuide-Agent and compare:

- task success rate,
- public and hidden test pass rates,
- patch landing metrics such as `gold_file_patched` and `gold_function_patched`,
- patch size,
- no-hardcode rate,
- no-test-deletion rate,
- regression rate,
- leakage metrics,
- tool/step cost.

P3B implements baseline evaluation only:

```bash
python -m codeguide_agent.baselines.aider_runner \
  --root data/mini_repo_debug \
  --limit 5 \
  --output data/mini_repo_debug/reports/aider_baseline_report.json
```

If the `aider` CLI or required model/API configuration is not available, the
runner writes a skipped report and exits `0`. This keeps local validation
independent of paid API access.

The runner copies each task into an isolated temp workspace, removes
`metadata.json`, `gold.patch`, and `tests_hidden/` before invoking Aider,
builds the prompt only from `issue.md` and the public test command, and restores
hidden tests only after Aider exits for evaluator-side scoring. Hidden test
commands and logs are evaluator-only and must never be placed in the Aider
prompt.

Aider results are scored through the canonical CodeGuide reward and leakage
pipeline, including `codeguide_agent.reward.calculator`, patch metrics, strict
leakage metrics, and original-repo checksum checks. In `eval_compare`, Aider is
a real external baseline row; `gold` remains pipeline validation only.

## Teacher and Data Generator

Aider can generate candidate patches and repair explanations. Those outputs
should only enter teacher datasets after verifier filtering:

- public tests pass,
- hidden tests pass,
- patch size is reasonable,
- tests are not deleted or modified to cheat,
- no hardcoded expected outputs,
- changed files overlap suspicious or gold files,
- no unrelated file modifications.

Successful verified outputs can become SFT examples or DPO chosen responses.
P3B does not export teacher data yet.

## Repo-Map and Edit-Format Reference

The most useful Aider ideas to study are:

- repository symbol extraction,
- file ranking under token budget,
- issue-query related file selection,
- diff-like or search/replace edit formats,
- patch apply failure recovery,
- minimal edit preference.

These should be reimplemented in lightweight CodeGuide-native modules where
needed, subject to license compatibility and project scope.

## Minimal Runner Scope

`codeguide_agent/baselines/aider_runner.py` is now the canonical P3B Aider
baseline runner. It accepts a dataset root, limit, output path, temp root, and
timeout, then writes a JSON report with per-task skip/status, public and hidden
test results, patch metrics, reward metrics, leakage metrics, diff path, and
original-repo checksum status.
