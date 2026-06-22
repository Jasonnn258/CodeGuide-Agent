import os
import tempfile
from pathlib import Path

from task_071_lib.reader import read_file


def test_permission_error_propagates():
    # Reading a directory as a file should raise, not silently return ""
    with tempfile.TemporaryDirectory() as td:
        try:
            read_file(td)
        except (IsADirectoryError, PermissionError, OSError):
            pass
        else:
            raise AssertionError("expected OSError when reading a directory as a file")
