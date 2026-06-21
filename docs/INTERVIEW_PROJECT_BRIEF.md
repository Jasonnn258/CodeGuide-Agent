# CodeGuide-Agent 面试版项目说明

## 1. 一句话介绍

CodeGuide-Agent 是一个面向 coding agent 调试任务的数据闭环项目，核心是构建 Mini-Repo-Debug benchmark，采集真实 agent rollout，并把成功轨迹和失败轨迹转成可训练的 SFT / preference 数据包。

## 2. 我解决的问题

普通 coding agent 很容易出现 public tests 通过但 hidden tests 失败的情况。表面上模型修好了 bug，但实际补丁可能过窄、只适配样例、没有真正理解边界条件。

这个项目关注的不是单次 patch 成功，而是如何系统性发现这些失败模式，并把它们沉淀成后续训练可用的数据。

## 3. 我的方案

我把项目拆成一条完整 pipeline：

1. 构造 20 个 Mini-Repo-Debug 小仓库调试任务。
2. 每个任务包含 issue、public tests、hidden tests、metadata 和 gold patch。
3. 使用真实 DeepSeek coding agent 采集 rollout。
4. 对 rollout 做 public / hidden 诊断，识别成功、hidden fail、invalid action、leakage 等情况。
5. 成功轨迹导出为 SFT candidates。
6. public-pass-hidden-fail 轨迹和 gold patch 组成 preference pairs。
7. 对训练数据做 sanitization，避免 hidden tests、metadata、gold patch 路径和原始 stdout/stderr 泄漏到模型侧。
8. 构建 train-ready package、quality gate、dry-run trainer、replay eval 和 experiment scaffold。
9. 最后用 Makefile、clean-check 和 GitHub CI 做可复现验证。

## 4. 当前结果

- Mini-Repo-Debug 共 20 个任务。
- DeepSeek baseline：public pass rate 1.0，hidden pass rate 0.95，leakage rate 0.0。
- P5 导出 19 条 SFT candidates 和 1 条 hard preference pair。
- P9 扩展 preference bank 到 23 条 candidates，覆盖 20 个任务。
- P6 生成 train-ready package，并通过 quality gate。
- P7 实现 dry-run trainer 和 replay eval。
- P8 实现 mock artifact、trained policy interface 和 experiment eval scaffold。
- P10/P11 实现一键验证、clean-check、Makefile 和 runbook。
- P13 增加 GitHub Actions CI 和 release check。

## 5. 最关键的 case

task_009 是一个 optional default args 问题。模型修复了 mutable default list，但仍然会修改调用方显式传入的 tags 列表。

这个补丁 public tests 能过，但 hidden tests 会失败。因此它被标记为 public-pass-hidden-fail，并被构造成 preference pair：rejected 是模型补丁，chosen 是 gold patch。

这个 case 说明了项目的核心价值：我们不是只看 public pass，而是把 hidden generalization failure 转化为训练信号。

## 6. 面试官可能追问

### Q1：为什么要做 hidden tests？

因为 public tests 只能证明模型修了可见样例，不能证明补丁泛化。hidden tests 可以暴露过拟合 public tests、边界条件没处理、修改副作用等问题。

### Q2：为什么 successful rollout 可以做 SFT？

成功 rollout 里包含问题理解、工具调用、定位、修改和验证过程，可以作为 agent 行为模仿数据。它不只是 final answer，而是完整 trajectory。

### Q3：为什么 failed rollout 可以做 preference？

如果一个 rollout public pass 但 hidden fail，它往往很有训练价值。我们可以把它作为 rejected，把 gold patch 或更优 trajectory 作为 chosen，让模型学习什么样的 patch 更泛化。

### Q4：为什么要做 sanitization？

因为训练数据不能泄漏 hidden tests、metadata、gold patch 路径和原始测试输出。否则模型可能学到 oracle 信息，评估会失真。

### Q5：为什么现在没有直接训练？

当前阶段重点是把训练数据 pipeline 和质量门禁做扎实。真实训练需要更多 preference pairs 和更大任务规模，否则统计意义不够。现在的 dry-run trainer 是为了验证数据格式、质量门禁和实验闭环。

## 7. 可复现命令

make test

make clean-check

make validate-pipeline

scripts/release_check.sh

## 8. 简历表述

构建 CodeGuide-Agent coding-agent 训练数据闭环：设计 20-task Mini-Repo-Debug benchmark，采集真实 DeepSeek rollout，诊断 public-pass-hidden-fail 等失败模式，并导出 19 条 SFT candidates、1 条 hard preference pair 和 23 条 preference-bank candidates；实现数据 sanitization、train-ready package、quality gate、dry-run trainer、replay eval、experiment scaffold、Makefile clean-check 与 GitHub CI，保证训练前数据 pipeline 可复现、可审计。
