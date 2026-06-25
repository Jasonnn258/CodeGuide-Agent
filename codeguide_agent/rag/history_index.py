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

    @property
    def task_ids(self) -> set[str]:
        return {rec.task_id for rec in self.records}

    @property
    def generator_families(self) -> set[str]:
        return {rec.generator_family for rec in self.records if rec.generator_family}

    @property
    def patch_hashes(self) -> set[str]:
        return {rec.patch_hash for rec in self.records if rec.patch_hash}

    @property
    def issue_pattern_hashes(self) -> set[str]:
        return {rec.issue_pattern_hash for rec in self.records if rec.issue_pattern_hash}

    @property
    def splits(self) -> set[str]:
        return {rec.split for rec in self.records}

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
            score = _multi_field_score(query, rec)
            candidates.append((score, rec))
        candidates = _deterministic_sort(candidates)
        return [rec for _, rec in candidates[:top_k]]

    def retrieve_quality(
        self,
        query: str = "",
        top_k: int = 5,
        *,
        exclude_task_ids: set[str] | None = None,
        exclude_patch_hashes: set[str] | None = None,
    ) -> list[ExperienceRecord]:
        """Quality-mode retrieval: exclude only current task + exact patch hash.

        This maximizes recall for finding related experiences while preventing
        exact self-match. Use for offline evaluation and retrieval-quality
        measurement only — NOT safe for agent loop without additional filters.
        """
        exclude_task_ids = exclude_task_ids or set()
        exclude_patch_hashes = exclude_patch_hashes or set()

        candidates: list[tuple[float, ExperienceRecord]] = []
        for rec in self.records:
            if rec.task_id in exclude_task_ids:
                continue
            if rec.patch_hash in exclude_patch_hashes:
                continue
            score = _multi_field_score(query, rec)
            candidates.append((score, rec))
        candidates = _deterministic_sort(candidates)
        return [rec for _, rec in candidates[:top_k]]

    def retrieve_strict(
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
        """Strict safety-mode retrieval: exclude all five leakage dimensions.

        This is the safe mode for agent loop — prevents template-level leakage
        by also filtering generator_family and issue_pattern_hash matches.
        Coverage may be lower than quality mode, but leakage risk is minimal.
        """
        return self.retrieve(
            query=query,
            top_k=top_k,
            exclude_task_ids=exclude_task_ids,
            exclude_generator_families=exclude_generator_families,
            exclude_patch_hashes=exclude_patch_hashes,
            exclude_issue_pattern_hashes=exclude_issue_pattern_hashes,
            exclude_splits=exclude_splits,
        )

    def get_coverage(
        self,
        *,
        exclude_task_ids: set[str] | None = None,
        exclude_generator_families: set[str] | None = None,
        exclude_patch_hashes: set[str] | None = None,
        exclude_issue_pattern_hashes: set[str] | None = None,
        exclude_splits: set[str] | None = None,
    ) -> int:
        """Return how many records remain after applying exclusion filters.

        Returns 0 if all records are excluded — this is the "silently empty"
        guard that tests must catch.
        """
        exclude_task_ids = exclude_task_ids or set()
        exclude_generator_families = exclude_generator_families or set()
        exclude_patch_hashes = exclude_patch_hashes or set()
        exclude_issue_pattern_hashes = exclude_issue_pattern_hashes or set()
        exclude_splits = exclude_splits or set()

        count = 0
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
            count += 1
        return count

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


def _extract_issue_text(source: dict[str, Any]) -> str:
    """Extract issue text from SFT or preference record."""
    # Preference records have a direct 'prompt' field
    prompt = source.get("prompt", "")
    if prompt:
        return prompt
    # SFT records have messages array with user content
    messages = source.get("messages", [])
    for msg in messages:
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _extract_issue_summary(issue_text: str) -> str:
    """Extract just the issue description parts, stripping agent instruction prefix."""
    # Look for the "Issue:\n" section
    parts = issue_text.split("Issue:\n", 1)
    if len(parts) > 1:
        return parts[1].strip()
    # Fallback: try to find "# " title line
    for line in issue_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return issue_text.strip()


def _derive_generator_family(source: dict[str, Any], task_id: str) -> str:
    """Derive generator_family from source data or task characteristics."""
    # Preference records may have source_policy
    policy = source.get("source_policy", "")
    if policy:
        return policy

    # Try to derive from issue title keywords
    issue_text = _extract_issue_text(source)
    summary = _extract_issue_summary(issue_text).lower()

    # Keyword-based categorization
    keyword_map = {
        "yaml": "config_parsing",
        "config": "config_parsing",
        "json": "data_parsing",
        "csv": "data_parsing",
        "parse": "parsing",
        "path": "path_handling",
        "import": "import_handling",
        "validate": "validation",
        "email": "validation",
        "sort": "sorting",
        "filter": "filtering",
        "empty": "edge_case_empty",
        "none": "edge_case_none",
        "null": "edge_case_null",
        "upper": "text_transform",
        "lower": "text_transform",
        "text": "text_transform",
        "crash": "error_handling",
        "error": "error_handling",
        "format": "formatting",
        "version": "version_handling",
        "missing": "missing_implementation",
        "helper": "helper_function",
        "nested": "nested_structure",
    }
    for keyword, family in keyword_map.items():
        if keyword in summary:
            return family

    # Fallback: derive from task_id range
    try:
        num = int(task_id.split("_")[-1])
        if num <= 20:
            return "basic_repair"
        elif num <= 40:
            return "intermediate_repair"
        elif num <= 60:
            return "advanced_repair"
        else:
            return "complex_repair"
    except (ValueError, IndexError):
        return "unknown"


def _make_experience_record(
    task_id: str,
    source: dict[str, Any],
    repos: Path,
    kind: str,
    exp_id: str = "",
) -> ExperienceRecord:
    if not exp_id:
        exp_id = f"{task_id}_gold_reference"

    # Gold patch: try train_package data first, then repo file
    gold_patch = ""
    if kind == "sft":
        gold_patch = source.get("final_patch", "")
    elif kind == "preference":
        chosen = source.get("chosen", {})
        gold_patch = chosen.get("final_patch", "")

    gold_patch_path = repos / task_id / "gold.patch"
    if not gold_patch and gold_patch_path.exists():
        gold_patch = gold_patch_path.read_text(encoding="utf-8")

    patch_hash = hashlib.sha256(gold_patch.encode()).hexdigest()[:16] if gold_patch else ""

    # Extract issue text from actual data schema
    issue_text = _extract_issue_text(source)
    issue_summary = _extract_issue_summary(issue_text)
    issue_pattern_hash = hashlib.sha256(issue_text.encode()[:200]).hexdigest()[:16] if issue_text else ""

    generator_family = _derive_generator_family(source, task_id)

    # Extract failure signal
    if kind == "preference":
        rejection_reason = source.get("rejection_reason", "")
        reason_labels = source.get("reason_labels", [])
        failure_signal = rejection_reason or (", ".join(reason_labels) if reason_labels else "")
    else:
        reward = source.get("reward_summary", {})
        failure_signal = reward.get("hidden_failure_type", "")
        if not failure_signal or failure_signal == "none":
            failure_signal = "public_passes"

    # Target files from localization
    localization = source.get("localization", {})
    target_files = localization.get("gold_files", [])

    # Build patch_summary from the diff without including the full diff
    patch_summary = _summarize_patch(gold_patch)

    # Negative rollouts for preference records
    negative_rollouts = []
    if kind == "preference":
        rejected = source.get("rejected", {})
        if rejected:
            negative_rollouts.append({
                "trajectory_id": rejected.get("trajectory_id", ""),
                "rejection_reason": source.get("rejection_reason", ""),
                "reason_labels": source.get("reason_labels", []),
            })

    storage_view = {
        "gold_patch": gold_patch,
        "negative_rollouts": negative_rollouts,
    }

    retrieval_view = {
        "issue_summary": _truncate(issue_summary, 500),
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
    """Deterministic term-overlap relevance score (0.0–1.0)."""
    if not query:
        return 0.0
    doc_lower = document.lower()
    terms = query.lower().split()
    score = 0.0
    for term in terms:
        if term in doc_lower:
            score += 1.0
        else:
            # Penalize missing terms slightly for better discrimination
            score += 0.0
    return score / max(1, len(terms))


def _multi_field_score(query: str, rec: "ExperienceRecord") -> float:
    """Deterministic multi-field scoring using retrieval_view fields.

    Weights:
      - issue_summary:     0.40
      - failure_signal:    0.25
      - patch_summary:     0.20
      - changed_files:     0.10
      - strategy:          0.05

    Tie-breaking: lexicographic by experience_id for full determinism.
    """
    if not query:
        return 0.0
    rv = rec.retrieval_view
    fields = {
        "issue_summary": 0.40,
        "failure_signal": 0.25,
        "patch_summary": 0.20,
        "changed_files": 0.10,
        "strategy": 0.05,
    }
    score = 0.0
    for field, weight in fields.items():
        text = rv.get(field, "")
        if isinstance(text, list):
            text = " ".join(text)
        score += weight * _simple_relevance(query, text)
    return score


def _deterministic_sort(candidates: list[tuple[float, "ExperienceRecord"]]) -> list[tuple[float, "ExperienceRecord"]]:
    """Sort candidates by score descending, then by experience_id for determinism."""
    return sorted(candidates, key=lambda x: (-x[0], x[1].experience_id))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
