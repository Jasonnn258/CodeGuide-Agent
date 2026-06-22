from task_098_lib.seed import ensure_seeded


def test_conflicting_seed_raises():
    ensure_seeded(42)
    try:
        ensure_seeded(99)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError for conflicting seed")
