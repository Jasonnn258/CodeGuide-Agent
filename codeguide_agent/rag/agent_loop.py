"""History RAG agent-loop integration — off-by-default, leakage-safe.

This module connects the offline History RAG index to the agent loop via
ContextPack.  It is **disabled by default** and must be explicitly enabled
via config flag or CLI.

Usage pattern::

    from codeguide_agent.rag.agent_loop import HistoryRAGAgentLoop

    loop = HistoryRAGAgentLoop(index_path, enabled=True)
    history_context = loop.build_history_context(task_id="task_042", issue_text="...")
    pack = context_mgr.build_pack(issue=..., history_rag=history_context)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from codeguide_agent.rag.history_index import HistoryIndex

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_MAX_SNIPPETS = 3
DEFAULT_MAX_CHARS_PER_SNIPPET = 600


@dataclass
class HistoryRAGConfig:
    """Configuration for History RAG agent-loop integration."""

    enabled: bool = False
    index_path: str = "data/mini_repo_debug/history_index/experience_records.jsonl"
    mode: str = "quality"  # only quality mode is supported for agent loop
    max_snippets: int = DEFAULT_MAX_SNIPPETS
    max_chars_per_snippet: int = DEFAULT_MAX_CHARS_PER_SNIPPET
    same_family_warn_threshold: int = 3  # warn if this many top results share family


# ---------------------------------------------------------------------------
# Agent-loop integration
# ---------------------------------------------------------------------------


@dataclass
class HistoryRAGContext:
    """Result of building history context for one task."""

    snippets: list[dict[str, str]] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    excluded_task_ids: list[str] = field(default_factory=list)
    excluded_patch_hashes: list[str] = field(default_factory=list)
    same_family_warning: bool = False
    same_family_warning_detail: str = ""
    leakage_safe: bool = True
    leakage_violations: list[str] = field(default_factory=list)
    total_available: int = 0

    def to_context_pack_dicts(self) -> list[dict[str, str]]:
        """Return list of dicts suitable for ContextManager.build_pack(history_rag=...)."""
        return self.snippets


class HistoryRAGAgentLoop:
    """Off-by-default History RAG connector for the agent loop.

    Only quality mode is supported (exclude task_id + patch_hash).
    Strict/strict_full modes are for offline evaluation only.
    """

    def __init__(self, config: HistoryRAGConfig | None = None) -> None:
        self.config = config or HistoryRAGConfig()
        self._index: HistoryIndex | None = None
        self._safety_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.config.enabled = value

    @property
    def index(self) -> HistoryIndex:
        if self._index is None:
            path = Path(self.config.index_path)
            self._index = HistoryIndex.load(path) if path.exists() else HistoryIndex()
        return self._index

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------

    def build_history_context(
        self,
        task_id: str,
        issue_text: str,
        patch_hash: str = "",
    ) -> HistoryRAGContext:
        """Build leakage-safe history snippets for one task.

        Returns a HistoryRAGContext.  When disabled, returns empty context.
        """
        ctx = HistoryRAGContext(
            excluded_task_ids=[task_id],
            excluded_patch_hashes=[patch_hash] if patch_hash else [],
            total_available=len(self.index.records),
        )

        if not self.config.enabled:
            self._log("history_rag_disabled", task_id=task_id)
            return ctx

        if not issue_text.strip():
            self._log("history_rag_empty_query", task_id=task_id)
            return ctx

        # --- retrieve (quality mode: task_id + patch_hash only) ---
        retrieved = self.index.retrieve_quality(
            query=issue_text,
            top_k=self.config.max_snippets,
            exclude_task_ids={task_id},
            exclude_patch_hashes={patch_hash} if patch_hash else set(),
        )

        ctx.retrieved_ids = [r.experience_id for r in retrieved]

        # --- same-family warning guard ---
        trigger_count = 0
        for r in retrieved:
            # Try to determine if any retrieved record shares the query task's family
            pass  # actual check below
        ctx.same_family_warning, ctx.same_family_warning_detail = self._check_same_family(
            task_id, retrieved
        )

        # --- build safe snippets ---
        for r in retrieved:
            snippet = self._build_safe_snippet(r)
            ctx.snippets.append(snippet)

        # --- leakage check on built snippets ---
        ctx.leakage_safe, ctx.leakage_violations = self._check_snippet_leakage(ctx.snippets)

        self._log(
            "history_rag_built",
            task_id=task_id,
            retrieved_count=len(retrieved),
            snippet_count=len(ctx.snippets),
            same_family_warning=ctx.same_family_warning,
            leakage_safe=ctx.leakage_safe,
        )

        return ctx

    # ------------------------------------------------------------------
    # safety guards
    # ------------------------------------------------------------------

    def _check_same_family(
        self,
        task_id: str,
        retrieved: list,
    ) -> tuple[bool, str]:
        """Warn if all top results share the same generator_family as the query task.

        This is a template-leakage warning — not a hard block.
        """
        if len(retrieved) < self.config.same_family_warn_threshold:
            return False, ""

        # Find query task's family from the index
        query_family = ""
        for rec in self.index.records:
            if rec.task_id == task_id:
                query_family = rec.generator_family
                break

        if not query_family:
            return False, ""

        same_count = sum(1 for r in retrieved if r.generator_family == query_family)
        if same_count >= self.config.same_family_warn_threshold:
            return True, (
                f"All {same_count}/{len(retrieved)} top results share "
                f"generator_family='{query_family}' with query task {task_id}. "
                f"Consider using strict mode or adding manual review."
            )
        return False, ""

    def _build_safe_snippet(self, record) -> dict[str, str]:
        """Build a single safe snippet from an ExperienceRecord.

        Only includes retrieval_view fields — never full diff, hidden tests, or oracle.
        """
        rv = record.retrieval_view
        text_parts = []

        issue = rv.get("issue_summary", "")
        if issue:
            text_parts.append(f"Issue: {issue[:200]}")

        failure = rv.get("failure_signal", "")
        if failure:
            text_parts.append(f"Failure: {failure[:150]}")

        patch = rv.get("patch_summary", "")
        if patch:
            text_parts.append(f"Fix: {patch[:150]}")

        strategy = rv.get("strategy", "")
        if strategy:
            text_parts.append(f"Strategy: {strategy[:100]}")

        files = rv.get("changed_files", [])
        if files:
            text_parts.append(f"Files: {', '.join(files[:5])}")

        full_text = " | ".join(text_parts)

        # Cap at max chars
        if len(full_text) > self.config.max_chars_per_snippet:
            full_text = full_text[: self.config.max_chars_per_snippet - 3] + "..."

        return {
            "retrieval_text": full_text,
            "experience_id": record.experience_id,
            "task_id": record.task_id,
            "generator_family": record.generator_family,
            "patch_hash": record.patch_hash,
        }

    def _check_snippet_leakage(self, snippets: list[dict[str, str]]) -> tuple[bool, list[str]]:
        """Verify no forbidden content leaked into snippets."""
        forbidden = ["diff --git", "gold.patch", "hidden_test", "tests_hidden", "oracle", "evaluator"]
        violations = []
        for s in snippets:
            text = (s.get("retrieval_text", "") + json.dumps(s)).lower()
            for term in forbidden:
                if term.replace("_", "") in text.replace("_", ""):
                    violations.append(f"{s.get('experience_id', '?')}: '{term}' detected in snippet")
        return len(violations) == 0, violations

    # ------------------------------------------------------------------
    # safety log
    # ------------------------------------------------------------------

    def _log(self, event: str, **kwargs: Any) -> None:
        self._safety_log.append({"event": event, **kwargs})

    def get_safety_log(self) -> list[dict[str, Any]]:
        return list(self._safety_log)

    def clear_safety_log(self) -> None:
        self._safety_log.clear()

    def get_safety_report(self) -> dict[str, Any]:
        """Return a summary safety report."""
        built_events = [e for e in self._safety_log if e.get("event") == "history_rag_built"]
        disabled_events = [e for e in self._safety_log if e.get("event") == "history_rag_disabled"]
        warnings = sum(1 for e in built_events if e.get("same_family_warning"))
        leaks = sum(1 for e in built_events if not e.get("leakage_safe", True))
        return {
            "total_calls": len(self._safety_log),
            "built_count": len(built_events),
            "disabled_count": len(disabled_events),
            "same_family_warnings": warnings,
            "leakage_events": leaks,
            "safe": leaks == 0,
        }


# ---------------------------------------------------------------------------
# module-level convenience
# ---------------------------------------------------------------------------


def create_history_rag_loop(
    enabled: bool = False,
    index_path: str = "data/mini_repo_debug/history_index/experience_records.jsonl",
    max_snippets: int = DEFAULT_MAX_SNIPPETS,
    max_chars_per_snippet: int = DEFAULT_MAX_CHARS_PER_SNIPPET,
) -> HistoryRAGAgentLoop:
    """Factory for the most common configuration."""
    config = HistoryRAGConfig(
        enabled=enabled,
        index_path=index_path,
        mode="quality",
        max_snippets=max_snippets,
        max_chars_per_snippet=max_chars_per_snippet,
    )
    return HistoryRAGAgentLoop(config)
