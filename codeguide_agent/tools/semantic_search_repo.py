"""Semantic code search tool — hybrid retrieval for intent-based code finding.

Distinct from `search_repo` (exact keyword/regex).  Use this when you need
to find code by intent ("where is config parsing?") rather than by exact
string match ("config_loader").
"""

from __future__ import annotations

from pathlib import Path

from codeguide_agent.rag.retriever import HybridRetriever


def semantic_search_repo(
    repo_path: str | Path,
    query: str,
    max_matches: int = 10,
    prefer_functions: bool = True,
) -> dict:
    """Hybrid code search using lexical + structural + path signals.

    Args:
        repo_path: Path to the repository root directory.
        query: Natural language query describing what you're looking for.
        max_matches: Maximum number of results to return (default 10).
        prefer_functions: If True, boost function/method chunks (default True).

    Returns:
        dict with keys:
            tool_name: "semantic_search_repo"
            status: "success" | "error"
            query: the original query string
            matches: list of match dicts with file, name, type, line, content, score
            total_indexed: total chunks indexed for this repo
    """
    repo_path = Path(repo_path)
    if not repo_path.is_dir():
        return {
            "tool_name": "semantic_search_repo",
            "status": "error",
            "error": f"repo_path not found or not a directory: {repo_path}",
        }

    try:
        retriever = HybridRetriever(index_root=repo_path)
    except Exception as exc:
        return {
            "tool_name": "semantic_search_repo",
            "status": "error",
            "error": f"Failed to build index: {exc}",
        }

    results = retriever.search(
        query=query,
        top_k=max_matches,
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
            "end_line": c.end_line,
            "content_preview": c.content[:250],
            "score": round(r["score"], 4),
        })

    return {
        "tool_name": "semantic_search_repo",
        "status": "success",
        "query": query,
        "total_indexed": retriever.total_chunks,
        "matches": matches,
    }
