from task_084_lib.formatting import format_table


def test_input_columns_not_mutated():
    rows = [{"a": 1, "b": 2, "c": 3}]
    cols = ["b", "a"]
    format_table(rows, columns=cols)
    assert cols == ["b", "a"]


def test_input_columns_order_preserved():
    rows = [{"x": 10, "y": 20}]
    cols = ["y", "x"]
    format_table(rows, columns=cols)
    assert cols == ["y", "x"]
