# CodeGuide-Agent Design v0.6

This lightweight historical design anchor records the early project direction:
CodeGuide-Agent is a verifier-driven repo-level debugging research platform,
not a generic coding assistant.

The initial core loop is:

```text
Issue + mini repo + failing tests
-> inspect repository
-> localize likely fault
-> produce minimal patch
-> run public and hidden verifiers
-> log trajectory
-> calculate reward
```

Primary modules:

- Mini-Repo-Debug dataset.
- Local deterministic tools.
- Public/hidden test evaluator.
- Patch safety checks.
- JSONL trajectory logging.

Out of scope for v0.6: model training, GRPO, Aider integration, IDE completion,
VLM workflows, and large benchmark expansion.
