# CodeGuide-Agent 文档索引

## 面试官 / 招聘方快速阅读

建议按这个顺序看：

1. README.zh-CN.md
2. docs/INTERVIEW_PROJECT_BRIEF.md
3. docs/RESUME_BULLETS.md
4. docs/PROJECT_STORY.md

这条路径主要回答：项目解决什么问题、为什么有价值、当前做到什么程度、简历怎么表述。

## 想复现实验的人

建议看：

1. docs/P11_REPRODUCIBLE_RUNBOOK.md
2. Makefile
3. scripts/release_check.sh
4. docs/P13_CI_RELEASE_CHECK.md
5. docs/P15_MODEL_FACING_AUDIT.md

## 想看训练数据 pipeline 的人

建议看：

1. docs/CANONICAL_TRAINING_DATA_PIPELINE.md
2. codeguide_agent/dataset/export_training_candidates.py
3. codeguide_agent/dataset/prepare_training_package.py
4. codeguide_agent/dataset/expand_preference_candidates.py
5. docs/P23_P30_TRAINING_EXECUTION_PACK.md

## 想看训练入口的人

建议看：

1. docs/P23_P30_TRAINING_EXECUTION_PACK.md
2. requirements-training.txt
3. configs/training/sft_qwen2_5_coder_lora.json
4. codeguide_agent/training/build_hf_training_data.py
5. codeguide_agent/training/real_sft_lora_train.py

注意：当前数据规模适合 smoke training，不适合宣称 meaningful training。
