from task_098_lib.seed import ensure_seeded


def test_first_call_works():
    import random
    ensure_seeded(42)
    a = random.random()
    random.seed(42)
    b = random.random()
    assert a == b
