from task_081_lib.ini_reader import parse_ini_section


def test_parses_simple_keys():
    result = parse_ini_section("host=localhost\nport=5432")
    assert result == {"host": "localhost", "port": "5432"}


def test_skips_hash_comments():
    result = parse_ini_section("# config file\nkey=value")
    assert result == {"key": "value"}
