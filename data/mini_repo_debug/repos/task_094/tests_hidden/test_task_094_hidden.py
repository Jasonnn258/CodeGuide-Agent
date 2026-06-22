from task_094_lib.orchestrator import enrich


def test_enriches_with_custom_id_key():
    lookup = {"u1": "Alice", "u2": "Bob"}
    record = {"user_id": "u2", "score": 90}
    result = enrich(record, lookup, id_key="user_id")
    assert result["full_name"] == "Bob"


def test_custom_id_key_missing():
    lookup = {"u1": "Alice"}
    record = {"uid": "u99", "score": 10}
    result = enrich(record, lookup, id_key="uid")
    assert result["full_name"] == "Unknown"
