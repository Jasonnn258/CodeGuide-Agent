from task_094_lib.orchestrator import enrich


def test_enriches_with_default_id():
    lookup = {"u1": "Alice", "u2": "Bob"}
    record = {"id": "u1", "score": 100}
    result = enrich(record, lookup)
    assert result["full_name"] == "Alice"
    assert result["score"] == 100


def test_missing_id_returns_unknown():
    lookup = {"u1": "Alice"}
    record = {"id": "u99", "score": 50}
    result = enrich(record, lookup)
    assert result["full_name"] == "Unknown"
