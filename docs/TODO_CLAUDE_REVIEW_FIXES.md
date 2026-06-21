# TODO: Claude Review 修复清单

## 当前结论

项目工程闭环 v1 已经基本完成，可以作为阶段性成果展示。
但在投简历、给面试官或继续训练前，需要先处理 Claude review 提出的 P0/P1 问题。

当前最重要的边界：

- 可以说：完成了 coding-agent training data pipeline、smoke training entry、CI、audit、clean-check。
- 不要说：已经完成真实有效训练、实现 GRPO、训练出了可用 coding agent。

## P0：必须先修

### P0-1 修复 Markdown 文档字面 \n 渲染 bug

受影响文件：

- README.md
- docs/PROJECT_STORY.md
- docs/RESUME_BULLETS.md
- docs/INTERVIEW_PROJECT_BRIEF.md

问题：文件里存在反斜杠+n 两个字符，而不是真正换行。GitHub 渲染会乱。

验收标准：

- grep -RIn "\\n" README.md docs/PROJECT_STORY.md docs/RESUME_BULLETS.md docs/INTERVIEW_PROJECT_BRIEF.md 不再命中大段文档内容。
- GitHub 上标题、段落、列表正常渲染。
- 增加 make docs-check，防止回归。

### P0-2 明确 canonical SFT 数据构建入口

当前风险：可能存在多个 SFT builder：

- training_data/build_sft_from_trajectories.py
- data_builders/build_sft.py
- codeguide_agent/dataset/export_training_candidates.py

目标：

- 保留 codeguide_agent/dataset/export_training_candidates.py 作为 canonical P5 入口。
- 老脚本要么删除，要么改成 thin wrapper。
- README、Makefile、docs 全部指向同一条 canonical pipeline。

### P0-3 简历表达边界

必须保留这句话的含义：

- 当前数据规模是 19 SFT / 23 preference / 1 hard preference。
- 已经具备 smoke training 入口。
- 尚未达到 meaningful training 的数据阈值。

## P1：下一轮做

### P1-1 给 docs 加索引

新增 docs/INDEX.md，按读者路径组织：

- 面试官阅读路径
- 复现实验路径
- training data pipeline 路径
- training entry 路径

### P1-2 trajectory 记录具体 model/config

当前 model 字段过泛，例如 rollout_llm。
后续应记录：

- provider
- model
- temperature
- max_tokens
- endpoint profile
- run_id

### P1-3 eval_mini_repo.py 增加注释

明确 evaluators.patch_eval.evaluate_patch 是 diagnostic-only，不参与最终 reward，避免未来 reward 分叉。

## P2：数据规模上来后做

- 扩到 100+ active tasks。
- 收集 150+ SFT records。
- 收集 100+ preference records。
- 收集 30+ hard public-pass-hidden-fail preference records。
- 再跑真实 Qwen2.5-Coder LoRA SFT。
- 有训练前后 eval 对比后，再在简历里写训练结果。

## 当前下一步执行顺序

1. 修复字面 \n 文档渲染。
2. 增加 docs-check。
3. 增加 docs/INDEX.md。
4. 增加 docs/CANONICAL_TRAINING_DATA_PIPELINE.md。
5. 扫描所有 SFT builder 引用。
6. 再决定删除还是 wrapper 化 legacy builder。
