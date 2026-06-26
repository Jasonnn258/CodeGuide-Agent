"""Hybrid code index — BM25 lexical + AST metadata + path proximity.

No FAISS, no Chroma, no embeddings. Pure Python, deterministic scoring.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from codeguide_agent.rag.chunking import CodeChunk, chunk_directory


@dataclass
class CodeIndexEntry:
    """One indexed chunk with pre-computed term frequencies."""

    chunk: CodeChunk
    tf: dict[str, float] = field(default_factory=dict)  # term -> normalized TF
    idf: dict[str, float] = field(default_factory=dict)  # populated at build time


class HybridCodeIndex:
    """Hybrid index over code chunks with multi-signal scoring."""

    def __init__(self) -> None:
        self.entries: list[CodeIndexEntry] = []
        # Inverted index: term -> list of entry indices
        self._inverted: dict[str, list[int]] = defaultdict(list)
        # Document frequencies
        self._df: dict[str, int] = defaultdict(int)
        # Import graph: file -> set of imported module paths
        self._import_graph: dict[str, set[str]] = defaultdict(set)
        # Reverse import: module -> files that import it
        self._imported_by: dict[str, set[str]] = defaultdict(set)
        # Test mention: test_file -> {source_files referenced}
        self._test_mentions: dict[str, set[str]] = defaultdict(set)
        # File list for path proximity
        self._all_files: set[str] = set()
        # Stats
        self._total_docs: int = 0

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def add_chunk(self, chunk: CodeChunk) -> None:
        """Add one chunk to the index."""
        entry = CodeIndexEntry(chunk=chunk)
        entry.tf = _compute_tf(chunk.content)
        self.entries.append(entry)
        self._total_docs += 1

        # Update inverted index
        for term in entry.tf:
            self._inverted[term].append(len(self.entries) - 1)
            self._df[term] = self._df.get(term, 0) + 1

        self._all_files.add(chunk.file_path)

    def build_from_directory(self, root: str | Path) -> int:
        """Index all Python files in a directory. Returns number of chunks."""
        chunks = chunk_directory(root)
        for chunk in chunks:
            self.add_chunk(chunk)
        self._build_graphs(root)
        self._finalize_idf()
        return len(self.entries)

    def _build_graphs(self, root: str | Path) -> None:
        """Build import graph and test mention graph."""
        root = Path(root)
        for entry in self.entries:
            fpath = entry.chunk.file_path
            for imp in entry.chunk.imports:
                self._import_graph[fpath].add(imp)
                self._imported_by[imp].add(fpath)

        # Test mention: scan test files for references to source modules
        for entry in self.entries:
            fpath = entry.chunk.file_path
            if "test" in Path(fpath).stem.lower():
                content = entry.chunk.content.lower()
                # Heuristic: test file mentions source module names
                for other_entry in self.entries:
                    other_path = other_entry.chunk.file_path
                    other_stem = Path(other_path).stem
                    if other_stem in content:
                        self._test_mentions[fpath].add(other_path)

    def _finalize_idf(self) -> None:
        """Compute IDF for all terms."""
        for entry in self.entries:
            for term in entry.tf:
                entry.idf[term] = math.log((self._total_docs + 1) / (self._df.get(term, 0) + 1)) + 1.0

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        return len(self.entries)

    @property
    def unique_files(self) -> int:
        return len(self._all_files)

    @property
    def unique_terms(self) -> int:
        return len(self._inverted)

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
        """Hybrid search across lexical + structural + path signals.

        Returns list of dicts with keys: chunk, score, lexical_score,
        structural_score, path_score, import_score, test_mention_score.
        """
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for i, entry in enumerate(self.entries):
            chunk = entry.chunk

            # Optional file filter
            if file_filter and file_filter not in chunk.file_path:
                continue

            # 1. Lexical score (BM25-like)
            lexical = _bm25_score(query_terms, entry)

            # 2. Structural score (chunk type preference)
            structural = _structural_score(chunk, prefer_functions)

            # 3. Path proximity
            path = _path_proximity_score(chunk.file_path, path_bias) if path_bias else 1.0

            # 4. Import relation
            import_s = _import_score(chunk, self._import_graph) if path_bias else 1.0

            # 5. Test mention
            test_s = _test_mention_score(chunk, self._test_mentions) if path_bias else 1.0

            # Weighted combination
            total = (
                0.50 * lexical
                + 0.15 * structural
                + 0.15 * path
                + 0.10 * import_s
                + 0.10 * test_s
            )

            scored.append((total, {
                "chunk": chunk,
                "score": total,
                "lexical_score": lexical,
                "structural_score": structural,
                "path_score": path,
                "import_score": import_s,
                "test_mention_score": test_s,
            }))

        # Deterministic sort: score desc, then symbol_id for tie-break
        scored.sort(key=lambda x: (-x[0], x[1]["chunk"].symbol_id))
        return [item for _, item in scored[:top_k]]

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize index metadata (not chunks — those are rebuilt)."""
        return {
            "total_chunks": self._total_docs,
            "unique_files": len(self._all_files),
            "unique_terms": len(self._inverted),
            "files": sorted(self._all_files),
            "import_graph": {k: sorted(v) for k, v in self._import_graph.items()},
            "imported_by": {k: sorted(v) for k, v in self._imported_by.items()},
        }

    def save_chunks(self, path: Path) -> None:
        """Save all chunks as JSONL."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                c = entry.chunk
                rec = {
                    "file_path": c.file_path,
                    "name": c.name,
                    "chunk_type": c.chunk_type,
                    "content": c.content,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "parent_name": c.parent_name,
                    "docstring": c.docstring,
                    "symbol_id": c.symbol_id,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    @classmethod
    def load_chunks(cls, path: Path) -> HybridCodeIndex:
        """Load index from saved chunks JSONL."""
        idx = cls()
        if not path.exists():
            return idx
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            chunk = CodeChunk(
                file_path=d["file_path"],
                name=d["name"],
                chunk_type=d["chunk_type"],
                content=d["content"],
                start_line=d["start_line"],
                end_line=d["end_line"],
                parent_name=d.get("parent_name", ""),
                docstring=d.get("docstring", ""),
            )
            idx.add_chunk(chunk)
        return idx


# ---------------------------------------------------------------------------
# scoring helpers
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric + underscore, filter short."""
    import re
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    # Also split compound identifiers on underscores
    result: list[str] = []
    for t in tokens:
        if "_" in t and len(t) > 3:
            result.extend(p for p in t.split("_") if len(p) >= 2)
        result.append(t)
    return [t for t in result if len(t) >= 2]


def _compute_tf(content: str) -> dict[str, float]:
    """Compute normalized term frequency."""
    tokens = _tokenize(content)
    if not tokens:
        return {}
    tf = defaultdict(float)
    for t in tokens:
        tf[t] += 1.0
    # Normalize
    max_freq = max(tf.values())
    return {t: f / max_freq for t, f in tf.items()}


def _bm25_score(query_terms: list[str], entry: CodeIndexEntry, k1: float = 1.2, b: float = 0.75) -> float:
    """BM25-like score — deterministic, no randomness."""
    score = 0.0
    for term in query_terms:
        tf = entry.tf.get(term, 0.0)
        if tf == 0:
            continue
        idf = entry.idf.get(term, 1.0)
        score += idf * (tf * (k1 + 1)) / (tf + k1)
    return score / max(1, len(query_terms))


def _structural_score(chunk: CodeChunk, prefer_functions: bool) -> float:
    """Score chunk based on type and metadata quality."""
    base = 0.5
    if chunk.chunk_type == "function":
        base = 1.0 if prefer_functions else 0.8
    elif chunk.chunk_type == "method":
        base = 0.9 if prefer_functions else 0.7
    elif chunk.chunk_type == "class":
        base = 0.8
    elif chunk.chunk_type == "module_docstring":
        base = 0.6
    # Bonus for docstring
    if chunk.docstring:
        base = min(1.0, base + 0.1)
    # Bonus for short, focused chunks
    lines = chunk.content.count("\n") + 1
    if 3 <= lines <= 30:
        base = min(1.0, base + 0.1)
    return base


def _path_proximity_score(file_path: str, bias_path: str) -> float:
    """Score based on directory similarity. Closer paths = higher score."""
    if not bias_path:
        return 1.0
    fp = Path(file_path)
    bp = Path(bias_path)
    # Compute common prefix depth
    fp_parts = fp.parts
    bp_parts = bp.parts
    common = 0
    for a, b in zip(fp_parts, bp_parts):
        if a == b:
            common += 1
        else:
            break
    # Score: shared depth / max possible
    max_depth = max(len(fp_parts), len(bp_parts))
    if max_depth == 0:
        return 1.0
    return common / max_depth


def _import_score(chunk: CodeChunk, import_graph: dict[str, set[str]]) -> float:
    """Score based on how many query-relevant modules import this file."""
    imports = import_graph.get(chunk.file_path, set())
    # Files with more imports may be more central
    return min(1.0, len(imports) / 10.0)


def _test_mention_score(chunk: CodeChunk, test_mentions: dict[str, set[str]]) -> float:
    """Score based on whether test files reference this chunk's file."""
    mentions = 0
    for test_file, refs in test_mentions.items():
        if chunk.file_path in refs:
            mentions += 1
    return min(1.0, mentions / 5.0)
