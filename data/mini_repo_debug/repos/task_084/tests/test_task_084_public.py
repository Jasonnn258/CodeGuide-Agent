from task_084_lib.formatting import format_table


def test_formats_with_default_columns():
    rows = [{"name": "Ada", "age": 28}]
    result = format_table(rows)
    assert "name" in result
    assert "age" in result
    assert "Ada" in result


def test_formats_with_explicit_columns():
    rows = [{"name": "Ada", "age": 28, "city": "London"}]
    result = format_table(rows, columns=["name", "age"])
    lines = result.split("\n")
    assert len(lines) == 2


def test_empty_rows():
    assert format_table([]) == ""
