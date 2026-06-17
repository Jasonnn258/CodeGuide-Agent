from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeguide_agent.training_data.schemas import ChatMessage, SFTSample, SYSTEM_MESSAGE


def read_trajectory(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_sample(rows: list[dict[str, Any]], source_path: str | Path) -> SFTSample | None:
    if not rows:
        return None
    final = next((row for row in reversed(rows) if row.get("type") == "final"), None)
    if final is None:
        return None
    final_status = final.get("final_status", "")
    source_name = Path(source_path).name
    is_gold = "gold" in source_name or "gold" in final.get("trajectory_id", "")
    reward = final.get("reward", {})
    is_success = final_status == "success" or (reward.get("public_pass") and reward.get("hidden_pass"))
    if not is_success and not is_gold:
        return None

    task_id = final.get("task_id") or rows[0].get("task_id", "")
    messages = [
        ChatMessage("system", SYSTEM_MESSAGE),
        ChatMessage("user", f"Repair the repository for Mini-Repo-Debug task {task_id}. Use tools and verifier feedback."),
    ]
    for row in rows:
        if row.get("type") != "step":
            continue
        if _is_hidden_step(row):
            continue
        action_payload = {
            "thought": row.get("thought", ""),
            "action_name": row.get("action_name", ""),
            "action_input": _sanitize_payload(row.get("action_input", {})),
        }
        observation_payload = _sanitize_payload(row.get("observation", {}))
        messages.append(ChatMessage("assistant", json.dumps({"action": action_payload}, sort_keys=True)))
        messages.append(ChatMessage("tool", json.dumps({"observation": observation_payload}, sort_keys=True)))

    final_content = {
        "final_status": final_status,
        "stop_reason": final.get("stop_reason", ""),
        "final_patch": final.get("final_patch", ""),
    }
    messages.append(ChatMessage("assistant", json.dumps({"final": final_content}, sort_keys=True)))
    return SFTSample(
        messages=messages,
        metadata={
            "task_id": task_id,
            "trajectory_id": final.get("trajectory_id", ""),
            "source": str(source_path),
            "final_status": final_status,
            "is_gold": is_gold,
        },
    )


def build_sft_dataset(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    input_root = Path(input_path)
    output = Path(output_path)
    files = sorted(input_root.glob("*.jsonl")) if input_root.is_dir() else [input_root]
    samples = []
    for path in files:
        sample = build_sample(read_trajectory(path), path)
        if sample is not None:
            samples.append(sample)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_dict(), sort_keys=True) + "\n")
    return {"input_files": len(files), "samples_written": len(samples), "output": str(output)}


def _is_hidden_step(row: dict[str, Any]) -> bool:
    text = json.dumps(row, sort_keys=True)
    return "tests_hidden" in text


def _sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if key in {"gold_files", "gold_functions"}:
                continue
            sanitized[key] = _sanitize_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [_sanitize_payload(item) for item in payload]
    if isinstance(payload, str):
        return payload.replace("tests_hidden", "[hidden_tests]")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build chat-format SFT JSONL from trajectory JSONL files.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build_sft_dataset(args.input, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
