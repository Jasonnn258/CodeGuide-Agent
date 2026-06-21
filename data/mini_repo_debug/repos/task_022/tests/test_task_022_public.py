from pathlib import Path

from task_022_lib.paths import safe_join


def test_normalizes_simple_relative_path(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    result = safe_join(str(base), "./daily.txt")
    assert Path(result).resolve() == (base / "daily.txt").resolve()


def test_nested_relative_path(tmp_path):
    base = tmp_path / "reports"
    base.mkdir()
    result = safe_join(str(base), "2026/june.txt")
    assert Path(result).resolve() == (base / "2026" / "june.txt").resolve()
