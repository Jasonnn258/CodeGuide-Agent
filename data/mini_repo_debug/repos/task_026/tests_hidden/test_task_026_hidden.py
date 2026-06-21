from task_026_lib.config import load_config


def test_ignores_comment_lines():
    text = """// deployed by ops
{
  "enabled": true
}
"""
    assert load_config(text)["enabled"] is True


def test_allows_trailing_commas():
    assert load_config('{"hosts": ["a", "b",],}') == {"hosts": ["a", "b"]}
