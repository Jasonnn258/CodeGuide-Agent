from task_041_lib.parser import parse_assignment


def test_parses_simple_assignment():
    assert parse_assignment("host=localhost") == ("host", "localhost")


def test_strips_outer_whitespace():
    assert parse_assignment(" port = 5432 ") == ("port", "5432")
