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

The main runtime base is forge-agent style because it has clearer boundaries
for event logs, tool execution, and research trajectories.

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
- gold file hit,
- gold function hit,
- patch size,
- no-hardcode rate,
- no-test-deletion rate,
- regression rate,
- tool/step cost.

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

`codeguide_agent/baselines/aider_runner.py` is currently a CLI stub. The future
runner should accept a task repo, issue text, public test command, and hidden
test command, then return a patch, test results, and patch metrics using the
same report schema as the forge baseline.
