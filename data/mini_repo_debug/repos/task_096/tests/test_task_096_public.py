from task_096_lib.models import Item
from task_096_lib.cart import cart_total


def test_single_item():
    items = [Item(name="apple", price=1.0)]
    assert cart_total(items) == 1.0


def test_multiple_items():
    items = [Item(name="a", price=10.0), Item(name="b", price=5.0)]
    assert cart_total(items) == 15.0
