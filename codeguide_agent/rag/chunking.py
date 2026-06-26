"""AST-based code chunking — function, class, and file-level chunks.

Uses stdlib `ast` only — no tree-sitter dependency. Each chunk captures:
  - name (function/class name or file path)
  - chunk_type (function | class | module_docstring | file_level)
  - content (source text)
  - start_line, end_line
  - parent_name (enclosing class for methods, or "")
  - docstring (extracted docstring text, or "")
  - imports (list of imported module names)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CodeChunk:
    """One logical chunk of source code."""

    file_path: str
    name: str  # function/class name, or file stem for file-level
    chunk_type: str  # "function", "class", "method", "module_docstring", "file_level"
    content: str
    start_line: int
    end_line: int
    parent_name: str = ""  # enclosing class for methods
    docstring: str = ""
    imports: list[str] = field(default_factory=list)  # module-level imports
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def symbol_id(self) -> str:
        if self.parent_name:
            return f"{self.file_path}::{self.parent_name}.{self.name}"
        return f"{self.file_path}::{self.name}"


def chunk_file(file_path: str | Path, source: str | None = None) -> list[CodeChunk]:
    """Parse a Python file into AST chunks.

    Args:
        file_path: Path to the .py file.
        source: Optional source text. If None, read from file_path.

    Returns:
        List of CodeChunks: module_docstring (if any), then top-level classes
        and functions, then file_level remainder.
    """
    file_path = str(file_path)
    if source is None:
        try:
            source = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return []

    if not source.strip():
        return []

    lines = source.splitlines()

    # Extract imports
    imports = _extract_imports(source)

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        # For unparseable files, return a single file-level chunk
        return [CodeChunk(
            file_path=file_path,
            name=Path(file_path).stem,
            chunk_type="file_level",
            content=source,
            start_line=1,
            end_line=len(lines),
            imports=imports,
        )]

    chunks: list[CodeChunk] = []

    # Module docstring
    docstring = ast.get_docstring(tree)
    if docstring:
        ds_node = _find_docstring_node(tree)
        ds_start = ds_node.lineno if ds_node else 1
        ds_end = ds_node.end_lineno if ds_node and hasattr(ds_node, 'end_lineno') else ds_start + len(docstring.splitlines())
        chunks.append(CodeChunk(
            file_path=file_path,
            name=f"{Path(file_path).stem}__doc",
            chunk_type="module_docstring",
            content=_extract_lines(lines, ds_start, ds_end or ds_start),
            start_line=ds_start,
            end_line=ds_end or ds_start,
            docstring=docstring,
            imports=imports,
        ))

    # Top-level classes and functions
    body_items = _top_level_defs(tree)
    covered_lines: set[int] = set()

    for node, name, kind in body_items:
        start = node.lineno
        end = getattr(node, 'end_lineno', start)
        if end is None:
            end = start

        if kind == "class":
            # Class chunk: include the full class body
            cls_doc = ast.get_docstring(node) or ""
            chunks.append(CodeChunk(
                file_path=file_path,
                name=name,
                chunk_type="class",
                content=_extract_lines(lines, start, end),
                start_line=start,
                end_line=end,
                docstring=cls_doc,
                imports=imports,
            ))
            # Methods within class
            for sub_node, sub_name, _ in _class_methods(node):
                m_start = sub_node.lineno
                m_end = getattr(sub_node, 'end_lineno', m_start)
                if m_end is None:
                    m_end = m_start
                m_doc = ast.get_docstring(sub_node) or ""
                chunks.append(CodeChunk(
                    file_path=file_path,
                    name=sub_name,
                    chunk_type="method",
                    content=_extract_lines(lines, m_start, m_end),
                    start_line=m_start,
                    end_line=m_end,
                    parent_name=name,
                    docstring=m_doc,
                    imports=imports,
                ))

        elif kind == "function":
            func_doc = ast.get_docstring(node) or ""
            chunks.append(CodeChunk(
                file_path=file_path,
                name=name,
                chunk_type="function",
                content=_extract_lines(lines, start, end),
                start_line=start,
                end_line=end,
                docstring=func_doc,
                imports=imports,
            ))

        for line_no in range(start, (end or start) + 1):
            covered_lines.add(line_no)

    # File-level remainder: everything not in named chunks
    uncovered = [l for l in range(1, len(lines) + 1) if l not in covered_lines and lines[l - 1].strip()]
    if uncovered:
        # Group contiguous uncovered lines
        groups = _group_contiguous(uncovered, max_gap=3)
        for group in groups:
            if len(group) >= 2:  # skip single-line gaps
                g_start, g_end = group[0], group[-1]
                content = _extract_lines(lines, g_start, g_end)
                if content.strip():
                    chunks.append(CodeChunk(
                        file_path=file_path,
                        name=f"{Path(file_path).stem}__L{g_start}",
                        chunk_type="file_level",
                        content=content,
                        start_line=g_start,
                        end_line=g_end,
                        imports=imports,
                    ))

    return chunks


def chunk_directory(
    root: str | Path,
    glob_pattern: str = "**/*.py",
    ignore_patterns: tuple[str, ...] = ("__pycache__", ".git", ".pytest_cache", "tests_hidden"),
) -> list[CodeChunk]:
    """Recursively chunk all Python files in a directory."""
    root = Path(root)
    chunks: list[CodeChunk] = []
    for py_file in sorted(root.glob(glob_pattern)):
        rel = str(py_file.relative_to(root))
        if any(pat in rel for pat in ignore_patterns):
            continue
        chunks.extend(chunk_file(str(py_file)))
    return chunks


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _extract_imports(source: str) -> list[str]:
    """Extract imported module names from Python source."""
    imports: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return sorted(set(imports))


def _top_level_defs(tree: ast.AST) -> list[tuple[ast.AST, str, str]]:
    """Return (node, name, kind) for top-level classes and functions."""
    result: list[tuple[ast.AST, str, str]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            result.append((node, node.name, "class"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append((node, node.name, "function"))
    return result


def _class_methods(cls_node: ast.ClassDef) -> list[tuple[ast.AST, str, str]]:
    """Return (node, name, kind) for methods within a class."""
    result: list[tuple[ast.AST, str, str]] = []
    for node in cls_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append((node, node.name, "method"))
    return result


def _find_docstring_node(tree: ast.Module) -> ast.AST | None:
    """Find the AST node for the module docstring."""
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        return tree.body[0]
    return None


def _extract_lines(lines: list[str], start: int, end: int) -> str:
    """Extract lines[start-1:end] joined."""
    return "\n".join(lines[max(0, start - 1):end])


def _group_contiguous(numbers: list[int], max_gap: int = 3) -> list[list[int]]:
    """Group a sorted list of integers into contiguous runs with allowed gaps."""
    if not numbers:
        return []
    numbers = sorted(numbers)
    groups: list[list[int]] = []
    current = [numbers[0]]
    for i in range(1, len(numbers)):
        if numbers[i] - current[-1] <= max_gap:
            current.append(numbers[i])
        else:
            groups.append(current)
            current = [numbers[i]]
    groups.append(current)
    return groups
