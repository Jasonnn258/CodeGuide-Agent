"""Dataset quality diagnostics for Mini-Repo-Debug.

Local offline scan of repos/task_* metadata + history_index/experience_records.jsonl.
No external APIs, no training, no LLM calls, no leakage of gold/hidden content.

Reports:
  - task counts and metadata completeness
  - source / split / difficulty / bug_type distribution
  - generator_family distribution (from experience_records.jsonl)
  - patch_hash and issue_pattern_hash duplication
  - gold_files / gold_functions overlap
  - template-leakage risk pairs (same generator_family + same patch_hash OR same issue_pattern_hash)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class DatasetQualityReport:
    report_version: str = "1.0"
    total_tasks: int = 0
    metadata_completeness: dict[str, Any] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    by_split: dict[str, int] = field(default_factory=dict)
    by_difficulty: dict[str, int] = field(default_factory=dict)
    by_bug_type: dict[str, int] = field(default_factory=dict)
    by_generator_family: dict[str, int] = field(default_factory=dict)
    patch_hash_duplicates: dict[str, list[str]] = field(default_factory=dict)
    issue_pattern_hash_duplicates: dict[str, list[str]] = field(default_factory=dict)
    gold_files_overlap_groups: list[dict[str, Any]] = field(default_factory=list)
    gold_functions_overlap_groups: list[dict[str, Any]] = field(default_factory=list)
    template_leakage_risk_pairs: list[dict[str, Any]] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)
    overall_status: str = "unknown"


REQUIRED_METADATA_FIELDS = (
    "task_id",
    "bug_type",
    "scenario",
    "difficulty",
    "repo_path",
    "source",
    "split",
    "gold_files",
    "gold_functions",
    "gold_patch",
    "public_test_cmd",
    "hidden_test_cmd",
)


def build_quality_report(root: Path | None = None) -> DatasetQualityReport:
    root = Path(root) if root else REPO_ROOT / "data" / "mini_repo_debug"
    repos_dir = root / "repos"
    history_path = root / "history_index" / "experience_records.jsonl"

    task_dirs = sorted(d for d in repos_dir.glob("task_*") if d.is_dir()) if repos_dir.exists() else []

    metadatas: list[dict[str, Any]] = []
    missing_fields_count: Counter[str] = Counter()
    file_presence: Counter[str] = Counter()
    total = len(task_dirs)

    for task_dir in task_dirs:
        meta_path = task_dir / "metadata.json"
        meta: dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        metadatas.append(meta)

        for field_name in REQUIRED_METADATA_FIELDS:
            val = meta.get(field_name)
            if val in (None, "", [], {}):
                missing_fields_count[field_name] += 1

        for required_file, presence_key in (
            ("metadata.json", "metadata_json_present"),
            ("issue.md", "issue_md_present"),
            ("gold.patch", "gold_patch_present"),
            ("README.md", "readme_md_present"),
        ):
            if (task_dir / required_file).exists():
                file_presence[presence_key] += 1
        for required_dir, presence_key in (
            ("src", "src_dir_present"),
            ("tests", "tests_dir_present"),
            ("tests_hidden", "tests_hidden_dir_present"),
        ):
            if (task_dir / required_dir).is_dir():
                file_presence[presence_key] += 1

    by_source = Counter(str(m.get("source", "") or "unknown") for m in metadatas)
    by_split = Counter(str(m.get("split", "") or "unknown") for m in metadatas)
    by_difficulty = Counter(str(m.get("difficulty", "") or "unknown") for m in metadatas)
    by_bug_type = Counter(str(m.get("bug_type", "") or "unknown") for m in metadatas)

    by_generator_family: Counter[str] = Counter()
    patch_hash_groups: dict[str, list[str]] = defaultdict(list)
    issue_pattern_hash_groups: dict[str, list[str]] = defaultdict(list)
    family_by_task: dict[str, str] = {}
    patch_hash_by_task: dict[str, str] = {}
    issue_pattern_hash_by_task: dict[str, str] = {}

    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            family = rec.get("generator_family", "") or ""
            ph = rec.get("patch_hash", "") or ""
            iph = rec.get("issue_pattern_hash", "") or ""
            task_id = rec.get("task_id", "") or ""
            if not task_id:
                continue
            is_gold = rec.get("experience_id", "").endswith("gold_reference")
            if task_id not in family_by_task or is_gold:
                if family:
                    family_by_task[task_id] = family
            if task_id not in patch_hash_by_task or is_gold:
                if ph:
                    patch_hash_by_task[task_id] = ph
            if task_id not in issue_pattern_hash_by_task or is_gold:
                if iph:
                    issue_pattern_hash_by_task[task_id] = iph

        for task_id, fam in family_by_task.items():
            by_generator_family[fam] += 1
        for task_id, ph in patch_hash_by_task.items():
            patch_hash_groups[ph].append(task_id)
        for task_id, iph in issue_pattern_hash_by_task.items():
            issue_pattern_hash_groups[iph].append(task_id)

    patch_hash_duplicates = {
        h: sorted(set(ts))
        for h, ts in patch_hash_groups.items()
        if h and len(set(ts)) >= 2
    }
    issue_pattern_hash_duplicates = {
        h: sorted(set(ts))
        for h, ts in issue_pattern_hash_groups.items()
        if h and len(set(ts)) >= 2
    }

    gold_files_groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    gold_functions_groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for meta in metadatas:
        tid = meta.get("task_id", "")
        if not tid:
            continue
        gf = tuple(sorted(meta.get("gold_files", []) or []))
        gfn = tuple(sorted(meta.get("gold_functions", []) or []))
        if gf:
            gold_files_groups[gf].append(tid)
        if gfn:
            gold_functions_groups[gfn].append(tid)
    gold_files_overlap_groups = [
        {"gold_files": list(key), "task_ids": sorted(set(ts))}
        for key, ts in gold_files_groups.items()
        if len(set(ts)) >= 2
    ]
    gold_files_overlap_groups.sort(key=lambda g: (-len(g["task_ids"]), g["task_ids"][0]))
    gold_functions_overlap_groups = [
        {"gold_functions": list(key), "task_ids": sorted(set(ts))}
        for key, ts in gold_functions_groups.items()
        if len(set(ts)) >= 2
    ]
    gold_functions_overlap_groups.sort(key=lambda g: (-len(g["task_ids"]), g["task_ids"][0]))

    risk_pairs: list[dict[str, Any]] = []
    task_ids_with_family = sorted(family_by_task.keys())
    for i, a in enumerate(task_ids_with_family):
        fa = family_by_task[a]
        pa = patch_hash_by_task.get(a, "")
        ia = issue_pattern_hash_by_task.get(a, "")
        for b in task_ids_with_family[i + 1:]:
            if family_by_task[b] != fa:
                continue
            pb = patch_hash_by_task.get(b, "")
            ib = issue_pattern_hash_by_task.get(b, "")
            shared_patch = bool(pa) and pa == pb
            shared_issue_pattern = bool(ia) and ia == ib
            if shared_patch or shared_issue_pattern:
                risk_pairs.append({
                    "task_a": a,
                    "task_b": b,
                    "generator_family": fa,
                    "shared_patch_hash": shared_patch,
                    "shared_issue_pattern_hash": shared_issue_pattern,
                })
    risk_pairs.sort(key=lambda r: (r["generator_family"], r["task_a"], r["task_b"]))

    flags: dict[str, Any] = {
        "has_metadata_for_all_tasks": all(m for m in metadatas) and total > 0,
        "metadata_field_missing": dict(missing_fields_count),
        "file_presence": {k: v for k, v in file_presence.items()},
        "patch_hash_duplicate_groups": len(patch_hash_duplicates),
        "issue_pattern_hash_duplicate_groups": len(issue_pattern_hash_duplicates),
        "gold_files_overlap_groups": len(gold_files_overlap_groups),
        "gold_functions_overlap_groups": len(gold_functions_overlap_groups),
        "template_leakage_risk_pair_count": len(risk_pairs),
        "history_index_available": history_path.exists(),
    }

    critical_missing = sum(1 for f in REQUIRED_METADATA_FIELDS if missing_fields_count[f] == total and total > 0)
    overall_status = "pass"
    if total == 0:
        overall_status = "fail"
    elif critical_missing > 0:
        overall_status = "fail"
    elif missing_fields_count["task_id"] > 0 or missing_fields_count["gold_files"] > 0 or missing_fields_count["gold_functions"] > 0:
        overall_status = "fail"

    return DatasetQualityReport(
        total_tasks=total,
        metadata_completeness={
            "total_tasks": total,
            "missing_field_counts": dict(missing_fields_count),
        },
        by_source=dict(by_source),
        by_split=dict(by_split),
        by_difficulty=dict(by_difficulty),
        by_bug_type=dict(by_bug_type),
        by_generator_family=dict(by_generator_family),
        patch_hash_duplicates=patch_hash_duplicates,
        issue_pattern_hash_duplicates=issue_pattern_hash_duplicates,
        gold_files_overlap_groups=gold_files_overlap_groups,
        gold_functions_overlap_groups=gold_functions_overlap_groups,
        template_leakage_risk_pairs=risk_pairs,
        flags=flags,
        overall_status=overall_status,
    )


def format_json(report: DatasetQualityReport) -> str:
    return json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n"


def format_markdown(report: DatasetQualityReport) -> str:
    lines: list[str] = []
    lines.append("# CodeGuide-Agent Dataset Quality Report")
    lines.append("")
    lines.append(f"- total_tasks: {report.total_tasks}")
    lines.append(f"- overall_status: {report.overall_status}")
    lines.append(f"- history_index_available: {report.flags.get('history_index_available')}")
    lines.append("")

    lines.append("## Metadata Completeness")
    lines.append("")
    mc = report.metadata_completeness
    lines.append(f"- total_tasks: {mc.get('total_tasks')}")
    missing = mc.get("missing_field_counts", {})
    if missing:
        lines.append("- missing_field_counts:")
        for f in REQUIRED_METADATA_FIELDS:
            if f in missing:
                lines.append(f"  - {f}: {missing[f]}")
    else:
        lines.append("- missing_field_counts: (none — all required fields populated)")
    lines.append("")

    lines.append("## File / Directory Presence")
    lines.append("")
    fp = report.flags.get("file_presence", {})
    lines.append("| artifact | present_count | out_of |")
    lines.append("|----------|---------------|--------|")
    for key in ("metadata_json_present", "issue_md_present", "gold_patch_present",
                "readme_md_present", "src_dir_present", "tests_dir_present",
                "tests_hidden_dir_present"):
        lines.append(f"| {key} | {fp.get(key, 0)} | {report.total_tasks} |")
    lines.append("")

    def _emit_counter(title: str, counter: dict[str, int]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not counter:
            lines.append("_(no data)_")
            lines.append("")
            return
        lines.append("| value | count |")
        lines.append("|-------|-------|")
        for k in sorted(counter.keys()):
            lines.append(f"| {k} | {counter[k]} |")
        lines.append("")

    _emit_counter("By Source", report.by_source)
    _emit_counter("By Split", report.by_split)
    _emit_counter("By Difficulty", report.by_difficulty)
    _emit_counter("By bug_type", report.by_bug_type)
    _emit_counter("By generator_family", report.by_generator_family)

    lines.append("## Patch Hash Duplicates")
    lines.append("")
    if not report.patch_hash_duplicates:
        lines.append("_(no duplicate patch_hash across distinct task_ids)_")
    else:
        lines.append("| patch_hash | task_ids |")
        lines.append("|------------|----------|")
        for h, tids in sorted(report.patch_hash_duplicates.items(), key=lambda kv: (-len(kv[1]), kv[1][0])):
            lines.append(f"| {h} | {', '.join(tids)} |")
    lines.append("")

    lines.append("## Issue Pattern Hash Duplicates")
    lines.append("")
    if not report.issue_pattern_hash_duplicates:
        lines.append("_(no duplicate issue_pattern_hash across distinct task_ids)_")
    else:
        lines.append("| issue_pattern_hash | task_ids |")
        lines.append("|---------------------|----------|")
        for h, tids in sorted(report.issue_pattern_hash_duplicates.items(), key=lambda kv: (-len(kv[1]), kv[1][0])):
            lines.append(f"| {h} | {', '.join(tids)} |")
    lines.append("")

    lines.append("## Gold Files Overlap Groups")
    lines.append("")
    if not report.gold_files_overlap_groups:
        lines.append("_(no exact gold_files list shared by 2+ tasks)_")
    else:
        for g in report.gold_files_overlap_groups:
            lines.append(f"- {g['gold_files']}: {', '.join(g['task_ids'])}")
    lines.append("")

    lines.append("## Gold Functions Overlap Groups")
    lines.append("")
    if not report.gold_functions_overlap_groups:
        lines.append("_(no exact gold_functions list shared by 2+ tasks)_")
    else:
        for g in report.gold_functions_overlap_groups:
            lines.append(f"- {g['gold_functions']}: {', '.join(g['task_ids'])}")
    lines.append("")

    lines.append("## Template Leakage Risk Pairs")
    lines.append("")
    lines.append("Distinct task_ids sharing generator_family AND (patch_hash OR issue_pattern_hash).")
    lines.append("")
    if not report.template_leakage_risk_pairs:
        lines.append("_(no template-leakage risk pairs detected)_")
    else:
        lines.append("| task_a | task_b | generator_family | shared_patch_hash | shared_issue_pattern_hash |")
        lines.append("|--------|--------|------------------|-------------------|---------------------------|")
        for r in report.template_leakage_risk_pairs:
            lines.append(
                f"| {r['task_a']} | {r['task_b']} | {r['generator_family']} | "
                f"{r['shared_patch_hash']} | {r['shared_issue_pattern_hash']} |"
            )
    lines.append("")

    lines.append("## Flags")
    lines.append("")
    for k, v in report.flags.items():
        if k in ("file_presence", "metadata_field_missing"):
            continue
        lines.append(f"- {k}: {v}")
    lines.append("")

    return "\n".join(lines) + "\n"
