from task_026_lib.config import load_config


def test_loads_plain_json_object():
    assert load_config('{"enabled": true, "retries": 3}') == {"enabled": True, "retries": 3}


def test_loads_nested_plain_json():
    assert load_config('{"service": {"name": "api"}}')["service"]["name"] == "api"
