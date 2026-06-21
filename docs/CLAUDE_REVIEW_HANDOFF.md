# Claude Review Handoff

## 当前阶段

CodeGuide-Agent 当前处于阶段性展示版本。项目已经完成 coding-agent training data pipeline 的工程闭环，包括：

- Mini-Repo-Debug benchmark
- real rollout mining
- SFT / preference export
- train-ready package
- quality gate
- dry-run trainer
- experiment scaffold
- clean-check
- leakage audit
- CI / release check
- smoke training entry

当前仍不宣称完成 meaningful training。

## 已修复的 Claude Review P0/P1 问题

### P0-1 Markdown 渲染问题

已修复 README、PROJECT_STORY、RESUME_BULLETS、INTERVIEW_PROJECT_BRIEF 中的字面 backslash-n 渲染 bug。

新增：

- make docs-check
- scripts/check_doc_rendering.py

### P0-2 Canonical SFT Pipeline

已明确 canonical training data pipeline：

1. codeguide_agent.dataset.export_training_candidates
2. codeguide_agent.dataset.prepare_training_package
3. codeguide_agent.dataset.expand_preference_candidates
4. codeguide_agent.training.build_hf_training_data
5. codeguide_agent.training.real_sft_lora_train

新增：

- docs/CANONICAL_TRAINING_DATA_PIPELINE.md
- make canonical-check
- scripts/check_canonical_training_pipeline.py

README 和 PHASE2 docs 不再推广 legacy SFT builder。

### P1-1 Docs Index

新增：

- docs/INDEX.md

用于给面试官、复现实验者、训练数据 pipeline 读者和训练入口读者提供阅读路径。

### P1-2 Trajectory Model Config Provenance

TrajectoryLogger 已支持 model_config 字段。

rollout collector 会尽量记录：

- provider
- model
- policy_name
- temperature
- max_tokens
- endpoint_profile
- run_id

prompt_only baseline 也记录 local provenance。

新增测试：

- tests/test_trajectory_logger_metadata.py

### P1-3 Diagnostic-only Patch Eval 注释

eval_mini_repo.py 中已标注 evaluate_patch 是 diagnostic-only，不参与最终 reward calculation。

## 当前验证结果

最近一次本地验证：

- make docs-check: PASS
- make canonical-check: PASS
- make test: 99 passed
- make clean-check: PASS
- make audit: PASS

## 当前边界

可以说：

- 项目完成了 coding-agent training data pipeline v1。
- 项目具备 smoke training entry。
- 项目有 clean-check、audit、CI、release check。
- 项目支持从 real rollout 中挖掘 SFT 和 preference 数据。

不要说：

- 已完成 meaningful training。
- 已训练出可用 coding agent。
- 已实现 GRPO。
- 已有最终训练收益。

当前数据规模：

- active tasks: 20
- SFT records: 19
- preference records: 23
- hard preference records: 1

## 希望二次 review 重点看

1. README / README.zh-CN / docs/INDEX.md 是否已经适合面试官快速理解。
2. canonical training data pipeline 是否清晰。
3. legacy SFT builder 是否还会造成误导。
4. trajectory model_config provenance 是否足够。
5. release_check 是否覆盖 docs-check / canonical-check / test / clean-check / audit。
6. 简历表达是否仍然过度包装。
7. 下一步是否应该继续扩数据，而不是继续补脚手架。
