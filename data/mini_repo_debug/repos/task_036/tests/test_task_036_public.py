from task_036_lib.receipt import render_receipt


def test_receipt_formats_positive_total():
    assert render_receipt(1234) == "Total: $12.34"
