import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_service import make_invoice


def test_invoice_without_tax_still_uses_subtotal():
    assert make_invoice([{"price": 4, "qty": 2}, {"price": 1}]) == {"total": 9}


def test_invoice_adds_tax():
    assert make_invoice([{"price": 10, "qty": 2}], tax=3) == {"total": 23}
