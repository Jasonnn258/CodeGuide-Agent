from task_096_lib.models import Item
from task_096_lib.cart import cart_total


def test_quantity_is_factored_in():
    items = [Item(name="apple", price=1.0, quantity=3)]
    assert cart_total(items) == 3.0


def test_mixed_quantities():
    items = [
        Item(name="a", price=2.0, quantity=5),
        Item(name="b", price=10.0, quantity=1),
    ]
    assert cart_total(items) == 20.0
