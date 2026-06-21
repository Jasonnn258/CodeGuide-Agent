from task_034_lib.discounts import apply_discount
from task_034_lib.orders import order_total


def test_discount_rounds_fractional_amounts():
    assert apply_discount(99, 5) == 94


def test_order_total_uses_rounded_discount():
    assert order_total([{"price": 99}], discount_percent=5) == 94
