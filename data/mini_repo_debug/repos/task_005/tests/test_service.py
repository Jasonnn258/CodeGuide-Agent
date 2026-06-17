import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from service import order_summary


def test_order_summary_applies_discount():
    order = {"items": [{"price": 10, "qty": 2}], "discount": 3}

    assert order_summary(order) == "$17"
