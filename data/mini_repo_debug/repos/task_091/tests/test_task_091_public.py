from task_091_lib.gateway import fetch_with_timeout


def test_invalid_url_returns_empty():
    result = fetch_with_timeout("not-a-valid-url")
    assert result == ""


def test_nonexistent_host_returns_empty():
    result = fetch_with_timeout("http://192.0.2.1.nonexistent.test/", timeout=0.1)
    assert result == ""
