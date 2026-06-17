import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from service import order_summary


def test_order_without_discount_still_formats_subtotal():
    order = {"items": [{"price": 4, "qty": 2}, {"price": 1}]}

    assert order_summary(order) == "$9"
