import tempfile
from pathlib import Path

from task_058_lib.fs import ensure_dir


def test_creates_new_directory():
    with tempfile.TemporaryDirectory() as td:
        new_dir = Path(td) / "subdir"
        ensure_dir(str(new_dir))
        assert new_dir.is_dir()
