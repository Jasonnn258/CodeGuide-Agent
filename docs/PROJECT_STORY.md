# CodeGuide-Agent 项目叙事

## 一句话总结

CodeGuide-Agent 是一个面向小型代码仓库调试任务的 agent training data pipeline，覆盖任务构造、真实 rollout 采集、失败模式诊断、SFT 和 preference 数据挖掘、训练包质量门禁、dry-run 训练脚手架、实验闭环和可复现验证。

## 背景问题

普通 LLM coding agent 在小仓库修 bug 时，经常出现 public tests 通过但 hidden tests 失败的问题。表面上模型能修复样例，但补丁可能过窄、修改副作用大、没有真正泛化。

本项目的核心目标不是单纯提高某个模型分数，而是构建一套可复现的 agent 训练数据闭环，用于发现、记录和利用这些失败轨迹。

## 方法路线

1. 构造 Mini-Repo-Debug benchmark，覆盖解析边界、路径处理、缓存 key、默认参数、日期边界、CLI 参数、异常处理、排序过滤等真实工程 bug 类型。
2. 对每个任务维护 public tests、hidden tests、metadata 和 gold patch，用 public-hidden gap 衡量泛化风险。
3. 采集真实 DeepSeek rollout，记录 agent actions、最终 patch 和 reward diagnostics。
4. 从成功轨迹导出 SFT candidates，从 public-pass-hidden-fail 轨迹导出 preference pairs。
5. 对导出的训练数据做 sanitization，禁止 hidden tests、metadata、gold patch 路径和原始 stdout/stderr 进入模型侧数据。
6. 构建 train-ready package、quality gate、dry-run trainer、replay eval 和 mock experiment loop。
7. 通过 clean-check 验证单元测试不依赖本地 generated trajectories，保证 clone 后可复现。

## 当前结果

- Mini-Repo-Debug 覆盖 20 个任务。
- 真实 DeepSeek baseline：public pass rate 1.0，hidden pass rate 0.95，leakage rate 0.0。
- P5 导出 19 条 SFT rollout candidates 和 1 条 hard preference pair。
- P9 扩展 preference bank 到 23 条 candidates，覆盖 20 个任务。
- P6 生成 train-ready package，并通过 quality gate。
- P7 提供 dry-run training scaffold 和 replay eval。
- P8 提供 mock artifact、trained policy interface 和 experiment eval scaffold。
- P10 提供一键离线 pipeline validation。
- P10.1 后，移走 data/mini_repo_debug/trajectories 后测试仍然 99 passed。
- P11 增加 Makefile、clean-check、clean-generated 和 reproducible runbook。

## 关键案例：task_009

task_009 是 optional default args 类型 bug。模型补丁修复了 mutable default list，但在显式传入 tags 参数时仍会原地修改调用方列表。因此 public tests 通过，hidden tests 失败。

这个案例被用于构造 preference pair：rejected 是 public-pass-hidden-fail 的 LLM patch，chosen 是 gold patch。它体现了本项目关注的核心问题：不是能否通过 public tests，而是补丁是否真正泛化。

## 面试表达

我做的不是简单跑一个 coding benchmark，而是搭了一套 agent 训练数据闭环。它从任务集构造开始，到真实 rollout 采集、失败诊断、SFT 和 preference 数据挖掘、数据安全清洗、训练包质量门禁、dry-run trainer、experiment scaffold，最后再通过 clean-check 保证工程可复现。

这个项目能体现三类能力：第一，理解 coding agent 的 public-hidden 泛化问题；第二，能设计可训练的数据结构和质量门禁；第三，能把实验 pipeline 工程化，而不是停留在 notebook 或一次性脚本。
