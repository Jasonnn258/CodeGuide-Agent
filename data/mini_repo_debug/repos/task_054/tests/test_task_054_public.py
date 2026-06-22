from task_054_lib.pipeline import build_pipeline


def test_single_step_pipeline():
    double = build_pipeline([lambda x: x * 2])
    assert double(5) == 10


def test_single_step_identity():
    identity = build_pipeline([lambda x: x])
    assert identity("hello") == "hello"
