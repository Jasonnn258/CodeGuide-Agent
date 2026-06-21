from task_030_lib.invoice import invoice_total
from task_030_lib.tax import tax_amount


def test_tax_amount_rounds_fractional_values():
    assert tax_amount(99, 5) == 5


def test_invoice_total_uses_rounded_tax():
    assert invoice_total([{"price": 99}], rate_percent=5) == 104
