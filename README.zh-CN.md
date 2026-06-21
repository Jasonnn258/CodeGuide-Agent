# CodeGuide-Agent 中文说明

## 项目简介

CodeGuide-Agent 是一个面向 coding agent 小仓库调试任务的训练数据闭环项目。项目围绕 Mini-Repo-Debug benchmark 构建，从任务集设计、真实 agent rollout 采集、失败模式诊断、SFT / preference 数据挖掘、训练包构建、质量门禁、dry-run 训练、实验 scaffold、可复现验证，到训练执行入口，形成了一套完整的 agent training data pipeline。

本项目重点解决的问题是：coding agent 在小仓库修 bug 时，经常出现 public tests 通过但 hidden tests 失败的情况。模型表面上修好了可见样例，但补丁可能过窄、没有处理边界条件、存在副作用，或者没有真正泛化。CodeGuide-Agent 将这些失败轨迹结构化记录下来，并转化为后续 SFT 或 preference training 可用的数据。

## 当前项目状态

当前版本可以认为是工程闭环 v1：

- 已构建 20 个 Mini-Repo-Debug 小仓库调试任务。
- 已采集真实 DeepSeek rollout baseline。
- 已完成 public / hidden 结果诊断与 hidden failure 类型分类。
- 已从成功轨迹导出 SFT candidates。
- 已从 public-pass-hidden-fail 轨迹导出 preference pair。
- 已构建 preference bank、train-ready package 和 quality gate。
- 已实现 dry-run trainer、replay eval、mock experiment artifact 和 trained policy interface。
- 已加入 Makefile、clean-check、release check、GitHub CI 和模型侧泄漏审计。
- 已提供 LoRA SFT 训练入口和 HF-style training data 转换脚本。

当前项目适合进行 smoke training 和面试展示，但还不适合宣称已经完成大规模有效训练。真实训练前仍需要扩容到 100+ tasks、150+ SFT records、100+ preference records、30+ hard preference records。

## 核心能力

### 1. Mini-Repo-Debug Benchmark

Mini-Repo-Debug 是一个小仓库 bug 修复 benchmark。每个任务包含：

- issue 描述
- buggy source code
- public tests
- hidden tests
- metadata
- gold patch
- rollout trajectory
- reward diagnostics

任务覆盖解析边界、路径处理、缓存 key、默认参数、边界条件、字符串归一化、字典 mutation、日期边界、JSON 配置解析、CLI 参数传递、异常处理、数值边界、排序过滤、服务集成、大小写处理等真实工程问题。

### 2. Public-Hidden Generalization Gap

本项目重点关注 public tests pass 但 hidden tests fail 的情况。这类失败说明模型可能只是修复了可见测试，而没有真正理解 bug 的泛化条件。

典型案例是 task_009。模型修复了 mutable default list 问题，但在显式传入 tags 参数时仍然会原地修改调用方列表。因此 public tests 通过，hidden tests 失败。这个失败轨迹被构造成 preference pair：rejected 是模型补丁，chosen 是 gold patch。

### 3. Rollout Mining

项目从真实 agent rollout 中挖掘训练数据：

- hidden pass 的成功轨迹可以导出为 SFT candidates。
- public-pass-hidden-fail 的失败轨迹可以和 gold patch 构造 preference pairs。
- invalid action、syntax error、no patch、public fail 等失败类型也可以进入 preference bank。

### 4. 数据安全与泄漏审计

模型侧训练数据不能泄漏 hidden tests、metadata、gold patch 路径、原始 stdout / stderr 等 oracle 信息。项目中加入了 sanitization 和 audit 机制，避免训练数据污染评估。

### 5. 训练前工程闭环

项目已经具备训练前所需的工程结构：

- train-ready package
- quality gate
- dry-run trainer
- replay eval
- HF-style training data converter
- LoRA SFT training script
- DPO readiness scaffold
- training preflight
- Makefile entrypoint
- CI / release check

## 当前结果

当前稳定版本的主要结果：

- Mini-Repo-Debug active tasks：20
- planned backlog tasks：80
- target total tasks：100
- SFT records：19
- preference records：23
- hard preference records：1
- clean-check：通过
- unit tests：99 passed
- tests 移除 generated trajectories 后仍通过
- 模型侧泄漏审计：已加入 make audit
- 训练入口：已加入 make training-data / make train-sft

当前 readiness 结论：

- 工程上已经可以 smoke training。
- 数据规模还不够支持严肃的最终训练结论。
- 下一步应重点扩任务、扩 rollout、扩 hard preference。

## 常用命令

运行单元测试：

    make test

验证测试不依赖本地 generated trajectories：

    make clean-check

运行模型侧泄漏审计：

    make audit

生成完整 pipeline 验证：

    make validate-pipeline

生成数据规模报告：

    make scale-report

生成训练数据：

    make training-data

训练前检查：

    make training-preflight

运行 SFT smoke training：

    make train-sft-smoke

运行 LoRA SFT：

    make train-sft

生成 rollout 批处理计划：

    make rollout-plan

检查是否达到真实训练门槛：

    make readiness

## 训练入口

在 GPU 机器上安装训练依赖：

    pip install -r requirements-training.txt

生成 HF-style 训练数据：

    make training-data

运行 tiny smoke train：

    make train-sft-smoke

运行 Qwen2.5-Coder LoRA SFT：

    make train-sft

默认配置文件：

- configs/training/sft_qwen2_5_coder_lora.json
- configs/training/sft_smoke_tiny.json

训练输出默认保存到：

- models/codeguide_sft_qwen2_5_coder_lora
- models/codeguide_sft_tiny_smoke

## 训练 readiness 标准

真实训练建议至少满足：

- active task count >= 100
- SFT records >= 150
- preference records >= 100
- hard preference records >= 30
- clean-check 通过
- leakage audit 通过
- train package quality gate 通过
- eval split 与 train split 明确隔离
- preference rejection reasons 足够多样

当前项目还未达到真实训练门槛，所以不应夸大为已经完成有效训练。当前更准确的表述是：训练数据 pipeline 和 smoke training 入口已经完成。

## 项目亮点

1. 不是简单 benchmark，而是完整 agent training data pipeline。
2. 不只看 public pass，而是重点分析 public-hidden generalization gap。
3. 同时支持 SFT 数据挖掘和 preference pair 构造。
4. 强调 hidden / oracle 信息不进入模型侧训练数据。
5. 有质量门禁、dry-run trainer、replay eval 和 experiment scaffold。
6. 有 clean-check、release check、GitHub CI 和 audit，工程可复现。
7. 已提供真实训练入口，但明确区分 smoke training 和 meaningful training。

## 面试表述

这个项目不是单纯让 coding agent 修几个 bug，而是围绕 coding agent 在小仓库调试中 public tests 通过但 hidden tests 失败的问题，构建了一套训练数据闭环。我设计了 Mini-Repo-Debug benchmark，采集真实 DeepSeek rollout，对成功轨迹导出 SFT candidates，对 hidden fail 轨迹构造 preference pairs，并实现了数据 sanitization、quality gate、dry-run trainer、experiment scaffold、clean-check、CI 和训练执行入口。当前工程已经能支持 smoke training，后续重点是扩容到 100+ tasks 和更多 hard preference pairs，再进行真实训练对比。

## 项目边界

已完成：

- 工程闭环 v1
- 训练数据构造流程
- 训练包与质量门禁
- smoke training 入口
- 可复现命令和 CI

未完成：

- 100+ active tasks
- 大规模真实 rollout
- 足量 hard preference pairs
- 正式 SFT / DPO 训练结果
- 训练前后 benchmark 对比

因此，本项目当前最准确的定位是：可复现的 coding-agent 训练数据 pipeline 和 smoke training 工程，而不是已经完成最终模型训练的项目。
