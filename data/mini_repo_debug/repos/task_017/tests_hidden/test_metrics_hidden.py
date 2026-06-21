import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import average


def test_average_with_negative_values():
    assert average([-2, 2]) == 0
