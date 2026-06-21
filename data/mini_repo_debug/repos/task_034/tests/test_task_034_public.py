from task_034_lib.orders import order_total


def test_order_total_applies_discount():
    assert order_total([{"price": 100}], discount_percent=10) == 90


def test_quantity_still_counts():
    assert order_total([{"price": 10, "quantity": 3}], discount_percent=0) == 30
