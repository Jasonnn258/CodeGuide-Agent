"""Hybrid code retriever — combines lexical, structural, path, import, and test-mention signals.

Usage:
    retriever = HybridRetriever(index_root="data/mini_repo_debug/repos/task_001")
    results = retriever.search("parse config file", top_k=5)
    for r in results:
        print(r["chunk"].symbol_id, r["score"])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codeguide_agent.rag.code_index import HybridCodeIndex


class HybridRetriever:
    """Deterministic hybrid code retriever."""

    def __init__(
        self,
        index_root: str | Path | None = None,
        index: HybridCodeIndex | None = None,
    ) -> None:
        self._index = index or HybridCodeIndex()
        self._built = index is not None
        if index_root and not self._built:
            self.build(index_root)

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def build(self, root: str | Path) -> int:
        """Build index from a source directory. Returns chunk count."""
        n = self._index.build_from_directory(root)
        self._built = True
        return n

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 10,
        *,
        prefer_functions: bool = True,
        path_bias: str = "",
        file_filter: str = "",
    ) -> list[dict[str, Any]]:
        """Hybrid search across indexed code.

        Args:
            query: Natural language or keyword query.
            top_k: Max results.
            prefer_functions: Boost function/method chunks.
            path_bias: If set, boost files in nearby directories.
            file_filter: If set, only return results from matching file paths.

        Returns:
            List of result dicts with keys: chunk, score, lexical_score,
            structural_score, path_score, import_score, test_mention_score.
        """
        if not self._built:
            return []
        return self._index.search(
            query=query,
            top_k=top_k,
            prefer_functions=prefer_functions,
            path_bias=path_bias,
            file_filter=file_filter,
        )

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------

    @property
    def index(self) -> HybridCodeIndex:
        return self._index

    @property
    def total_chunks(self) -> int:
        return self._index.total_chunks

    @property
    def built(self) -> bool:
        return self._built

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    @classmethod
    def from_chunks_file(cls, path: str | Path) -> HybridRetriever:
        """Load a retriever from a saved chunks JSONL file."""
        idx = HybridCodeIndex.load_chunks(Path(path))
        ret = cls(index=idx)
        ret._built = True
        return ret

    def save_chunks(self, path: str | Path) -> None:
        self._index.save_chunks(Path(path))


# ---------------------------------------------------------------------------
# convenience function
# ---------------------------------------------------------------------------


def semantic_search_repo(
    repo_path: str | Path,
    query: str,
    top_k: int = 10,
    *,
    prefer_functions: bool = True,
) -> dict[str, Any]:
    """Search repo code using hybrid retrieval (lexical + structural signals).

    This is a fallback/exploration tool, distinct from `search_repo` which
    does exact keyword matching. Use this when you need to find code by
    intent rather than exact string match.

    Args:
        repo_path: Path to the repository root.
        query: Natural language or keyword query.
        top_k: Max results to return.
        prefer_functions: Boost function/method chunks over file-level chunks.

    Returns:
        Dict with tool_name, status, matches list.
    """
    repo_path = Path(repo_path)
    retriever = HybridRetriever(index_root=repo_path)

    results = retriever.search(
        query=query,
        top_k=top_k,
        prefer_functions=prefer_functions,
        path_bias=str(repo_path),
    )

    matches = []
    for r in results:
        c = r["chunk"]
        matches.append({
            "file": c.file_path,
            "name": c.name,
            "type": c.chunk_type,
            "line": c.start_line,
            "content": c.content[:300],
            "score": round(r["score"], 4),
            "lexical_score": round(r["lexical_score"], 4),
        })

    return {
        "tool_name": "semantic_search_repo",
        "status": "success",
        "query": query,
        "top_k": top_k,
        "total_indexed_chunks": retriever.total_chunks,
        "matches": matches,
    }
