# CodeGuide-Agent Design v0.7

Design v0.7 expands the v0.6 Mini-Repo-Debug loop with clearer research
interfaces:

- fault localization metrics with gold file and gold function hits,
- patch minimality and safety metrics,
- process reward separate from outcome reward,
- baseline runners for deterministic local policies,
- trajectory logs suitable for future SFT/DPO/GRPO data builders.

The runtime should remain modular. The forge-style runtime package provides a
baseline/demo implementation of an agent loop, event log, tool registry, repo
context, LLM backend boundary, and CLI entry points. The canonical
Mini-Repo-Debug rollout path uses `RolloutCollector` plus
`codeguide_agent/tools/*`. CodeGuide-Agent owns the dataset, evaluation, reward,
and data builder layers.

Aider is treated as a strong baseline, teacher, and repo-map/edit-format
reference, not as the main implementation base.
