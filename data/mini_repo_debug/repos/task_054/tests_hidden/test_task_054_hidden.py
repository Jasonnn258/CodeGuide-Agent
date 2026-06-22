from task_054_lib.pipeline import build_pipeline


def test_two_step_pipeline():
    pipe = build_pipeline([lambda x: x + 1, lambda x: x * 3])
    assert pipe(5) == 18


def test_three_step_pipeline():
    pipe = build_pipeline([str, lambda s: s.upper(), lambda s: f"({s})"])
    assert pipe(42) == "(42)"
