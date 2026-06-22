from task_081_lib.ini_reader import parse_ini_section


def test_skips_semicolon_comments():
    result = parse_ini_section("; this is a comment\nname=alice")
    assert result == {"name": "alice"}


def test_strips_double_quotes_from_value():
    result = parse_ini_section('path="/usr/local/bin"')
    assert result == {"path": "/usr/local/bin"}


def test_empty_value_after_quotes():
    result = parse_ini_section('empty=""')
    assert result == {"empty": ""}
