from __future__ import annotations

import json

from codeguide_agent.trajectory.logger import TrajectoryLogger


def test_trajectory_logger_writes_model_config(tmp_path):
    path = tmp_path / "trajectory.jsonl"
    logger = TrajectoryLogger(
        path,
        task_id="task_x",
        trajectory_id="task_x_llm",
        model="deepseek-chat",
        model_config={
            "provider": "deepseek",
            "model": "deepseek-chat",
            "temperature": 0.0,
            "max_tokens": 4096,
            "endpoint_profile": "deepseek-default",
            "run_id": "run-001",
        },
    )

    logger.log_step("inspect", {}, {"ok": True}, "inspect repo")

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert rows[0]["model"] == "deepseek-chat"
    assert rows[0]["model_config"]["provider"] == "deepseek"
    assert rows[0]["model_config"]["temperature"] == 0.0
    assert rows[0]["model_config"]["endpoint_profile"] == "deepseek-default"
