CodeGuide-Agent runtime notice
==============================

The `codeguide_agent.runtime` package is a compact forge-style runtime adapted
from an earlier local prototype available in this workspace as
`/Users/yjx/Code/forge-agent`.

Provenance and license status:

- Local source path inspected: `/Users/yjx/Code/forge-agent`
- Local git remote: `https://github.com/muk610648-design/forge-agent.git`
- Local license/notice file: not present in the inspected checkout

Because no license file is present locally, CodeGuide-Agent does not describe
this runtime as an open-source dependency or ask readers to treat it as the
project's main research contribution. The adapted package is retained as a
baseline/demo runtime and reference implementation for:

- a small agent loop boundary,
- task/action/observation dataclasses,
- append-only JSONL event logs,
- a tool registry,
- bounded file/search/shell/test/git tools,
- lightweight repository context,
- an LLM backend router with deterministic fallback behavior.

The canonical Mini-Repo-Debug rollout path currently uses
`codeguide_agent.rollout.collector.RolloutCollector` and
`codeguide_agent/tools/*`, not `codeguide_agent/runtime/tools/*`.

CodeGuide-Agent's core contribution is the dataset, evaluation, reward,
trajectory, and training-data pipeline around repo-level debugging agents.
