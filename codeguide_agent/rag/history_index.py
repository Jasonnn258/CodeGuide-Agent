from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExperienceRecord:
    experience_id: str
    task_id: str
    split: str = "train"
    generator_family: str = ""
    patch_hash: str = ""
    issue_pattern_hash: str = ""

    storage_view: dict[str, Any] = field(default_factory=dict)
    retrieval_view: dict[str, Any] = field(default_factory=dict)
    visibility: dict[str, bool] = field(default_factory=lambda: {
        "allow_in_training": True,
        "allow_full_diff_in_retrieval_prompt": False,
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "task_id": self.task_id,
            "split": self.split,
            "generator_family": self.generator_family,
            "patch_hash": self.patch_hash,
            "issue_pattern_hash": self.issue_pattern_hash,
            "storage_view": self.storage_view,
            "retrieval_view": self.retrieval_view,
            "visibility": self.visibility,
        }


class HistoryIndex:
    def __init__(self) -> None:
        self.records: list[ExperienceRecord] = []

    def add(self, record: ExperienceRecord) -> None:
        self.records.append(record)

    def retrieve(
        self,
        query: str = "",
        top_k: int = 5,
        *,
        exclude_task_ids: set[str] | None = None,
        exclude_generator_families: set[str] | None = None,
        exclude_patch_hashes: set[str] | None = None,
        exclude_issue_pattern_hashes: set[str] | None = None,
        exclude_splits: set[str] | None = None,
    ) -> list[ExperienceRecord]:
        exclude_task_ids = exclude_task_ids or set()
        exclude_generator_families = exclude_generator_families or set()
        exclude_patch_hashes = exclude_patch_hashes or set()
        exclude_issue_pattern_hashes = exclude_issue_pattern_hashes or set()
        exclude_splits = exclude_splits or set()

        candidates: list[tuple[float, ExperienceRecord]] = []
        query_lower = query.lower()
        for rec in self.records:
            if rec.task_id in exclude_task_ids:
                continue
            if rec.generator_family in exclude_generator_families:
                continue
            if rec.patch_hash in exclude_patch_hashes:
                continue
            if rec.issue_pattern_hash in exclude_issue_pattern_hashes:
                continue
            if rec.split in exclude_splits:
                continue
            # simple BM25-like relevance via issue_summary overlap
            score = _simple_relevance(query_lower, rec.retrieval_view.get("issue_summary", ""))
            candidates.append((score, rec))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in candidates[:top_k]]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, path: Path) -> HistoryIndex:
        idx = cls()
        if not path.exists():
            return idx
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            rec = ExperienceRecord(
                experience_id=d["experience_id"],
                task_id=d["task_id"],
                split=d.get("split", "train"),
                generator_family=d.get("generator_family", ""),
                patch_hash=d.get("patch_hash", ""),
                issue_pattern_hash=d.get("issue_pattern_hash", ""),
                storage_view=d.get("storage_view", {}),
                retrieval_view=d.get("retrieval_view", {}),
                visibility=d.get("visibility", {"allow_in_training": True, "allow_full_diff_in_retrieval_prompt": False}),
            )
            idx.add(rec)
        return idx


def build_experience_records(
    root: Path,
    train_package_dir: str = "train_package",
    repos_dir: str = "repos",
) -> HistoryIndex:
    """Build HistoryIndex from train_package data and repo gold patches."""
    index = HistoryIndex()
    package = root / train_package_dir
    repos = root / repos_dir

    sft_records = _read_jsonl(package / "sft_train.jsonl") + _read_jsonl(package / "sft_eval.jsonl")
    pref_records = _read_jsonl(package / "preference_train.jsonl") + _read_jsonl(package / "preference_eval.jsonl")

    seen: set[str] = set()
    for source in sft_records:
        task_id = source.get("task_id", "")
        if not task_id or task_id in seen:
            continue
        seen.add(task_id)
        rec = _make_experience_record(task_id, source, repos, kind="sft")
        index.add(rec)

    for source in pref_records:
        task_id = source.get("task_id", "")
        exp_id = f"{task_id}_{source.get('policy', 'unknown')}"
        if exp_id in seen:
            continue
        seen.add(exp_id)
        rec = _make_experience_record(task_id, source, repos, kind="preference", exp_id=exp_id)
        index.add(rec)

    return index


def _make_experience_record(
    task_id: str,
    source: dict[str, Any],
    repos: Path,
    kind: str,
    exp_id: str = "",
) -> ExperienceRecord:
    if not exp_id:
        exp_id = f"{task_id}_gold_reference"

    gold_patch = ""
    gold_patch_path = repos / task_id / "gold.patch"
    if gold_patch_path.exists():
        gold_patch = gold_patch_path.read_text(encoding="utf-8")

    patch_hash = hashlib.sha256(gold_patch.encode()).hexdigest()[:16] if gold_patch else ""
    issue_text = source.get("issue", source.get("issue_text", ""))
    issue_pattern_hash = hashlib.sha256(issue_text.encode()[:200]).hexdigest()[:16] if issue_text else ""

    generator_family = source.get("bug_type", source.get("scenario", ""))
    failure_signal = source.get("expected_failure_mode", source.get("failure_signal", ""))
    target_files = source.get("target_files", source.get("changed_files", []))

    # Build a patch_summary from the diff without including the full diff
    patch_summary = _summarize_patch(gold_patch)

    storage_view = {
        "gold_patch": gold_patch,
        "negative_rollouts": source.get("negative_rollouts", []),
    }

    retrieval_view = {
        "issue_summary": _truncate(issue_text, 500),
        "failure_signal": failure_signal,
        "patch_summary": patch_summary,
        "changed_files": target_files,
        "strategy": f"{kind}: {generator_family} — {failure_signal[:200]}",
    }

    return ExperienceRecord(
        experience_id=exp_id,
        task_id=task_id,
        split=source.get("split", "train"),
        generator_family=generator_family,
        patch_hash=patch_hash,
        issue_pattern_hash=issue_pattern_hash,
        storage_view=storage_view,
        retrieval_view=retrieval_view,
        visibility={
            "allow_in_training": True,
            "allow_full_diff_in_retrieval_prompt": False,
        },
    )


def _summarize_patch(patch: str) -> str:
    if not patch:
        return "(no patch)"
    lines = patch.strip().split("\n")
    changed = []
    added = 0
    removed = 0
    for line in lines:
        if line.startswith("--- ") or line.startswith("+++ "):
            changed.append(line[4:].strip())
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    files = [f for f in changed if f]
    summary = f"Changed {len(files)} file(s): {', '.join(files)}. +{added}/-{removed} lines."
    return _truncate(summary, 300)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _simple_relevance(query: str, document: str) -> float:
    if not query:
        return 0.0
    doc_lower = document.lower()
    score = 0.0
    for term in query.split():
        if term in doc_lower:
            score += 1.0
    return score / max(1, len(query.split()))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
