from __future__ import annotations

from typing import Any

from codeguide_agent.evaluators.localization_eval import gold_file_hit, gold_function_hit
from codeguide_agent.reward.hacking_checks import count_changed_lines, detect_hardcode, modifies_tests


def evaluate_patch(
    diff_text: str,
    repo_path: str,
    gold_files: list[str],
    gold_functions: list[str],
    expected_outputs: list[str] | None = None,
) -> dict[str, Any]:
    hardcode = detect_hardcode(diff_text, expected_outputs=expected_outputs)
    return {
        "gold_file_hit": gold_file_hit(diff_text, gold_files),
        "gold_function_hit": gold_function_hit(diff_text, repo_path, gold_functions, gold_files),
        "patch_size": count_changed_lines(diff_text),
        "no_test_deletion": not modifies_tests(diff_text) and "deleted file mode" not in diff_text,
        "no_hardcode": not hardcode["hardcode_flag"],
        "hardcode_reasons": hardcode["reasons"],
    }
