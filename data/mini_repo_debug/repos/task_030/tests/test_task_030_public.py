from task_030_lib.invoice import invoice_total, subtotal


def test_subtotal_still_uses_quantity():
    assert subtotal([{"price": 10, "quantity": 2}, {"price": 5}]) == 25


def test_invoice_total_includes_simple_tax():
    assert invoice_total([{"price": 100}], rate_percent=10) == 110
