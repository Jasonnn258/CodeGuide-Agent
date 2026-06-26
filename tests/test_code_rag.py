from __future__ import annotations

from pathlib import Path

from codeguide_agent.rag.chunking import CodeChunk, chunk_file, chunk_directory
from codeguide_agent.rag.code_index import (
    HybridCodeIndex,
    _bm25_score,
    _compute_tf,
    _path_proximity_score,
    _structural_score,
    _tokenize,
)
from codeguide_agent.rag.retriever import HybridRetriever, semantic_search_repo
from codeguide_agent.tools.semantic_search_repo import semantic_search_repo as tool_semantic_search


# ---------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------

SAMPLE_PY = '''
"""Module docstring for testing."""

import os
from pathlib import Path


def parse_config(path: str) -> dict:
    """Parse a config file and return a dict."""
    with open(path) as f:
        return eval(f.read())


class ConfigLoader:
    """Loads and caches configurations."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    def load(self, name: str) -> dict:
        """Load named config."""
        return parse_config(f"{self.base_path}/{name}")
'''


def test_chunk_file_parses_classes_and_functions():
    chunks = chunk_file("test_mod.py", source=SAMPLE_PY)
    types = {c.chunk_type for c in chunks}
    assert "function" in types
    assert "class" in types
    assert "method" in types
    assert "module_docstring" in types


def test_chunk_function_has_correct_metadata():
    chunks = chunk_file("test_mod.py", source=SAMPLE_PY)
    func = [c for c in chunks if c.name == "parse_config"][0]
    assert func.chunk_type == "function"
    assert "Parse a config file" in func.docstring
    assert func.end_line >= func.start_line


def test_chunk_class_includes_methods():
    chunks = chunk_file("test_mod.py", source=SAMPLE_PY)
    cls_chunks = [c for c in chunks if c.chunk_type == "class"]
    assert len(cls_chunks) == 1
    assert cls_chunks[0].name == "ConfigLoader"
    method_chunks = [c for c in chunks if c.parent_name == "ConfigLoader"]
    assert len(method_chunks) >= 2  # __init__ + load


def test_chunk_symbol_id_format():
    chunks = chunk_file("test_mod.py", source=SAMPLE_PY)
    method = [c for c in chunks if c.name == "load"][0]
    assert "ConfigLoader.load" in method.symbol_id
    func = [c for c in chunks if c.name == "parse_config"][0]
    assert "::parse_config" in func.symbol_id


def test_chunk_empty_file():
    chunks = chunk_file("empty.py", source="")
    assert chunks == []


def test_chunk_syntax_error_file():
    chunks = chunk_file("bad.py", source="def foo(:")
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "file_level"


def test_chunk_file_with_imports():
    chunks = chunk_file("test_mod.py", source=SAMPLE_PY)
    func = [c for c in chunks if c.name == "parse_config"][0]
    assert "os" in func.imports or "pathlib" in func.imports


def test_chunk_directory(tmp_path):
    (tmp_path / "mod.py").write_text("def foo(): pass\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "bar.py").write_text("def bar(): pass\n")
    chunks = chunk_directory(tmp_path)
    assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# code index
# ---------------------------------------------------------------------------

def test_code_index_build_and_search():
    idx = HybridCodeIndex()
    chunk = CodeChunk(
        file_path="src/parser.py", name="parse_config", chunk_type="function",
        content="def parse_config(path):\n    with open(path) as f:\n        return eval(f.read())",
        start_line=1, end_line=3, docstring="Parse a config file.",
        imports=["os"],
    )
    idx.add_chunk(chunk)
    idx._finalize_idf()
    assert idx.total_chunks == 1

    results = idx.search("parse config file", top_k=5)
    assert len(results) >= 1


def test_code_index_search_with_file_filter():
    idx = HybridCodeIndex()
    idx.add_chunk(CodeChunk(
        file_path="src/a.py", name="foo", chunk_type="function", content="def foo(): pass",
        start_line=1, end_line=1,
    ))
    idx.add_chunk(CodeChunk(
        file_path="src/b.py", name="bar", chunk_type="function", content="def bar(): pass",
        start_line=1, end_line=1,
    ))
    idx._finalize_idf()

    results = idx.search("pass", top_k=10, file_filter="a.py")
    files = {r["chunk"].file_path for r in results}
    assert "src/a.py" in files
    assert "src/b.py" not in files


def test_code_index_deterministic():
    idx = HybridCodeIndex()
    for i in range(5):
        idx.add_chunk(CodeChunk(
            file_path=f"src/mod{i}.py", name=f"func_{i}", chunk_type="function",
            content=f"def func_{i}(): return {i}", start_line=1, end_line=1,
        ))
    idx._finalize_idf()
    r1 = idx.search("return", top_k=5)
    r2 = idx.search("return", top_k=5)
    assert [c["chunk"].symbol_id for c in r1] == [c["chunk"].symbol_id for c in r2]


# ---------------------------------------------------------------------------
# tokenization
# ---------------------------------------------------------------------------

def test_tokenize_splits_identifiers():
    tokens = _tokenize("def parse_config(path: str) -> dict:")
    assert "parse_config" in tokens or "parse" in tokens
    assert "path" in tokens
    assert "str" in tokens


def test_tokenize_filters_short():
    tokens = _tokenize("a b c def")
    assert "a" not in tokens
    assert "def" in tokens


def test_compute_tf_normalizes():
    tf = _compute_tf("foo foo bar")
    assert tf.get("foo", 0) == 1.0  # max frequency term
    assert tf.get("bar", 0) == 0.5  # half of max


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def test_structural_score_prefers_functions():
    func_chunk = CodeChunk("f.py", "my_func", "function", "def my_func(): pass", 1, 1)
    file_chunk = CodeChunk("f.py", "f__L1", "file_level", "x = 1", 1, 1)
    assert _structural_score(func_chunk, prefer_functions=True) > _structural_score(
        file_chunk, prefer_functions=True
    )


def test_path_proximity_score():
    assert _path_proximity_score("src/lib/parser.py", "src/lib") > 0.5
    assert _path_proximity_score("tests/test_foo.py", "src/lib") < 0.5
    assert _path_proximity_score("src/lib/parser.py", "") == 1.0


def test_bm25_score_positive_for_match():
    from codeguide_agent.rag.code_index import CodeIndexEntry
    chunk = CodeChunk("f.py", "foo", "function", "def parse_config(): pass", 1, 1)
    entry = CodeIndexEntry(chunk=chunk)
    entry.tf = _compute_tf("def parse_config(): pass")
    entry.idf = {t: 1.0 for t in entry.tf}
    terms = _tokenize("parse config")
    score = _bm25_score(terms, entry)
    assert score > 0


def test_bm25_score_zero_for_no_match():
    from codeguide_agent.rag.code_index import CodeIndexEntry
    chunk = CodeChunk("f.py", "foo", "function", "def foo(): pass", 1, 1)
    entry = CodeIndexEntry(chunk=chunk)
    entry.tf = _compute_tf("def foo(): pass")
    entry.idf = {t: 1.0 for t in entry.tf}
    terms = _tokenize("xyzabc notfound")
    score = _bm25_score(terms, entry)
    assert score == 0.0


# ---------------------------------------------------------------------------
# retriever
# ---------------------------------------------------------------------------

def test_retriever_build_and_search(tmp_path):
    (tmp_path / "parser.py").write_text('def parse_config(path):\n    """Parse config."""\n    pass\n')
    ret = HybridRetriever(index_root=tmp_path)
    assert ret.total_chunks >= 1
    results = ret.search("config parsing")
    assert len(results) >= 1
    assert results[0]["score"] >= 0


def test_retriever_from_chunks_file(tmp_path):
    (tmp_path / "mod.py").write_text("def foo(): pass\n")
    ret = HybridRetriever(index_root=tmp_path)
    chunks_path = tmp_path / "chunks.jsonl"
    ret.save_chunks(chunks_path)

    ret2 = HybridRetriever.from_chunks_file(chunks_path)
    assert ret2.total_chunks == ret.total_chunks


# ---------------------------------------------------------------------------
# semantic_search_repo tool
# ---------------------------------------------------------------------------

def test_semantic_search_tool(tmp_path):
    (tmp_path / "config.py").write_text('def load_config(path):\n    """Load config from file."""\n    pass\n')
    result = tool_semantic_search(str(tmp_path), "config loading")
    assert result["tool_name"] == "semantic_search_repo"
    assert result["status"] == "success"
    assert result["total_indexed"] >= 1


def test_semantic_search_tool_error_on_missing_dir():
    result = tool_semantic_search("/nonexistent/path", "query")
    assert result["status"] == "error"


def test_semantic_search_module_function(tmp_path):
    (tmp_path / "mod.py").write_text("def foo(): pass\n")
    result = semantic_search_repo(str(tmp_path), "foo")
    assert result["status"] == "success"
    assert len(result["matches"]) >= 1
