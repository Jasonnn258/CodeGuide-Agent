import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from text_cli import transform


def test_uppercase_flag_transforms_text():
    assert transform("Hello", uppercase=True) == "HELLO"
