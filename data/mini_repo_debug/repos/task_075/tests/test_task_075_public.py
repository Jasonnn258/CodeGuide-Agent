from task_075_lib.lookup import case_insensitive_get


def test_exact_match_works():
    headers = {"host": "localhost", "port": "8080"}
    assert case_insensitive_get(headers, "host") == "localhost"


def test_returns_none_for_missing():
    headers = {"host": "localhost"}
    assert case_insensitive_get(headers, "missing") is None
