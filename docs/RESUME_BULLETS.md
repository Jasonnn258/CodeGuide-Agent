# CodeGuide-Agent 简历 Bullet 素材

## 中文精简版

- 构建面向 coding agent 调试任务的 Mini-Repo-Debug 数据闭环，覆盖 20 个小仓库 bug 修复任务，包含 public/hidden tests、metadata、gold patch 与真实 rollout 诊断。
- 基于真实 DeepSeek rollout 设计训练数据挖掘流程：成功轨迹导出为 SFT candidates，public-pass-hidden-fail 轨迹与 gold patch 构造 preference pairs，产出 19 条 SFT candidates、1 条 hard preference pair，并扩展 preference bank 至 23 条 candidates。
- 实现训练数据 sanitization 与 quality gate，过滤 hidden tests、metadata、gold patch 路径和原始 stdout/stderr，降低数据泄漏和 oracle contamination 风险。
- 搭建 train-ready package、dry-run trainer、replay eval、mock experiment artifact 与 trained policy interface，形成训练前 agent data pipeline 的可复现实验闭环。
- 增加 Makefile、clean-check、release check 与 GitHub CI，验证单元测试在移除本地 generated trajectories 后仍可 99 passed，保证工程可复现性。

## 英文简历版

- Built a reproducible coding-agent training data pipeline around a 20-task Mini-Repo-Debug benchmark with public/hidden tests, metadata, gold patches, and real rollout diagnostics.
- Mined training candidates from real DeepSeek rollouts: exported successful trajectories as SFT candidates and converted public-pass-hidden-fail cases into preference pairs, producing 19 SFT candidates, 1 hard preference pair, and a 23-candidate preference bank.
- Implemented sanitization and quality gates to prevent hidden-test, metadata, gold-patch-path, and raw stdout/stderr leakage in model-facing training data.
- Developed train-ready package generation, dry-run training, replay evaluation, mock experiment artifacts, and a trained-policy interface to validate the pre-training experiment loop.
- Added Makefile entrypoints, clean-check, release-check, and GitHub CI; verified that tests still pass after removing generated local trajectories.

## 面试口语版

我这个项目不是单纯让 agent 修几个 bug，而是围绕 coding agent 的 public pass 但 hidden fail 问题，做了一套训练数据闭环。前面是 20 个小仓库调试任务和真实 DeepSeek rollout，后面把成功轨迹转成 SFT 数据，把 hidden fail 的轨迹转成 preference 数据。中间重点做了数据清洗、质量门禁、dry-run trainer 和实验 scaffold，最后用 clean-check 和 CI 保证 clone 下来之后也能复现。

## 技术关键词

- Coding Agent
- Rollout Mining
- Public-Hidden Generalization Gap
- SFT Data Construction
- Preference Pair Mining
- Data Sanitization
- Quality Gate
- Dry-run Trainer
- Replay Evaluation
- Experiment Scaffold
- Reproducible Pipeline
- CI / Clean-check
