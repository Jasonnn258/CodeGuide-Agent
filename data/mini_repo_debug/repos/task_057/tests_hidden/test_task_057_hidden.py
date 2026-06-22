from task_057_lib.counter import HitCounter


def test_reset_clears_overflow_flag():
    c = HitCounter(limit=2)
    c.hit()
    c.hit()
    c.hit()
    assert c.overflow is True
    c.reset()
    assert c.overflow is False


def test_reset_allows_fresh_overflow():
    c = HitCounter(limit=2)
    for _ in range(3):
        c.hit()
    c.reset()
    for _ in range(3):
        c.hit()
    assert c.overflow is True
