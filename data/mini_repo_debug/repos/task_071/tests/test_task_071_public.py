import tempfile
from pathlib import Path

from task_071_lib.reader import read_file


def test_reads_existing_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        f.flush()
        result = read_file(f.name)
        Path(f.name).unlink()
    assert result == "hello"


def test_missing_file_returns_empty():
    assert read_file("/tmp/nonexistent_xyz_file.txt") == ""
