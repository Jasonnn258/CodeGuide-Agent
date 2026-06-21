from task_036_lib.formatters import format_currency
from task_036_lib.receipt import render_receipt


def test_formatter_handles_negative_adjustment():
    assert format_currency(-50) == "-$0.50"


def test_receipt_uses_negative_format():
    assert render_receipt(-50) == "Total: -$0.50"
