from __future__ import annotations

from typing import Any

from codeguide_agent.reward.hacking_checks import (
    changed_files_from_diff,
    count_changed_lines,
    detect_hardcode,
    detect_unrelated_edits,
    hardcode_suspicion,
    modifies_tests,
)


HIDDEN_FAILURE_TYPES = {
    "none",
    "public_fail",
    "hidden_assertion_fail",
    "hidden_exception",
    "hidden_import_or_syntax",
    "hidden_timeout",
    "hidden_unknown",
}


def _passed(result: dict[str, Any] | None) -> bool:
    return bool(result and result.get("exit_code") == 0)


def classify_hidden_failure(public_pass: bool, hidden_result: dict[str, Any] | None) -> str:
    if not public_pass:
        return "public_fail"
    if hidden_result is None or _passed(hidden_result):
        return "none"
    text = "\n".join(str(hidden_result.get(key, "")) for key in ("status", "stdout", "stderr", "error"))
    lowered = text.lower()
    status = str(hidden_result.get("status", "")).lower()
    if hidden_result.get("exit_code") == 124 or status == "timeout" or "timeout" in lowered or "timed out" in lowered:
        return "hidden_timeout"
    if any(token in text for token in ("SyntaxError", "IndentationError", "ImportError", "ModuleNotFoundError")):
        return "hidden_import_or_syntax"
    if "AssertionError" in text or "assert " in text or "failed" in lowered:
        return "hidden_assertion_fail"
    if "Traceback" in text or "Exception" in text or "Error:" in text:
        return "hidden_exception"
    return "hidden_unknown"


def generalization_risk(
    public_pass_hidden_fail: bool,
    changed_lines: int,
    test_modified: bool,
    hardcode_flag: bool,
) -> tuple[str, bool]:
    patch_too_narrow = bool(public_pass_hidden_fail and changed_lines <= 2)
    if hardcode_flag or test_modified:
        return "high", patch_too_narrow
    if public_pass_hidden_fail:
        return "medium", patch_too_narrow
    return "low", False


def calculate_reward(
    public_result: dict[str, Any] | None,
    hidden_result: dict[str, Any] | None,
    diff_text: str,
    regression: bool | None = None,
    gold_files: list[str] | None = None,
    suspicious_files: list[str] | None = None,
    action_stats: dict[str, int] | None = None,
    expected_outputs: list[str] | None = None,
    fixture_names: list[str] | None = None,
    test_output_numbers: list[int | float] | None = None,
) -> dict[str, Any]:
    changed_files = changed_files_from_diff(diff_text)
    changed_lines = count_changed_lines(diff_text)
    public_pass = _passed(public_result)
    hidden_pass = _passed(hidden_result)
    test_modified = modifies_tests(diff_text)
    hardcode = detect_hardcode(diff_text, expected_outputs, fixture_names, test_output_numbers)
    hardcode_flag = hardcode["hardcode_flag"] or hardcode_suspicion(diff_text)
    public_pass_hidden_fail = bool(public_pass and hidden_result is not None and not hidden_pass)
    hidden_failure_type = classify_hidden_failure(public_pass, hidden_result)
    patch_generalization_risk, patch_too_narrow = generalization_risk(
        public_pass_hidden_fail,
        changed_lines,
        test_modified,
        hardcode_flag,
    )
    unrelated = detect_unrelated_edits(diff_text, gold_files, suspicious_files)
    regression_flag = bool(regression)
    action_stats = action_stats or {}
    invalid_action_count = sum(
        int(action_stats.get(key, 0))
        for key in ("invalid_json_count", "unknown_tool_count", "timeout_count", "duplicate_tool_calls")
    )

    reward = 0.0
    reward += 0.4 if public_pass else 0.0
    reward += 0.6 if hidden_pass else 0.0
    reward += 0.1 if len(changed_files) <= 2 else -0.1
    reward += 0.1 if changed_lines <= 30 else -0.1
    if test_modified:
        reward -= 0.3
    if hardcode_flag:
        reward -= 0.25
    if regression_flag:
        reward -= 0.3
    reward -= unrelated["unrelated_edit_penalty"]
    reward -= 0.1 * invalid_action_count

    return {
        "public_pass": public_pass,
        "hidden_pass": hidden_pass,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files,
        "changed_lines_count": changed_lines,
        "test_file_modified": test_modified,
        "hardcode_suspicion": hardcode_flag,
        "hardcode_reasons": hardcode["reasons"],
        "public_pass_hidden_fail": public_pass_hidden_fail,
        "hidden_failure_type": hidden_failure_type,
        "patch_generalization_risk": patch_generalization_risk,
        "patch_too_narrow": patch_too_narrow,
        "unrelated_edit_flag": unrelated["unrelated_edit_flag"],
        "unrelated_files": unrelated["unrelated_files"],
        "allowed_files": unrelated["allowed_files"],
        "allowed_overlap_ratio": unrelated["allowed_overlap_ratio"],
        "invalid_action_count": invalid_action_count,
        "action_stats": {
            "invalid_json_count": int(action_stats.get("invalid_json_count", 0)),
            "unknown_tool_count": int(action_stats.get("unknown_tool_count", 0)),
            "timeout_count": int(action_stats.get("timeout_count", 0)),
            "duplicate_tool_calls": int(action_stats.get("duplicate_tool_calls", 0)),
        },
        "regression": regression_flag,
        "total_reward": round(reward, 4),
    }
