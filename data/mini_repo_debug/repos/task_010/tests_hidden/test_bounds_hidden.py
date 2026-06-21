import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bounds import clamp_index


def test_negative_and_large_indexes_clamp():
    assert clamp_index(-3, 4) == 0
    assert clamp_index(99, 4) == 3
