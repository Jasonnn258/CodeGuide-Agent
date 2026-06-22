from task_075_lib.lookup import case_insensitive_get


def test_case_insensitive_match():
    headers = {"Host": "localhost"}
    assert case_insensitive_get(headers, "host") == "localhost"


def test_mixed_case_both_sides():
    headers = {"Content-Type": "application/json"}
    assert case_insensitive_get(headers, "content-type") == "application/json"
