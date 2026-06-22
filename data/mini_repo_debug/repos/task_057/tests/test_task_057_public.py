from task_057_lib.counter import HitCounter


def test_hit_increments_count():
    c = HitCounter(limit=10)
    c.hit()
    c.hit()
    assert c.count == 2


def test_reset_zeroes_count():
    c = HitCounter(limit=10)
    c.hit()
    c.hit()
    c.reset()
    assert c.count == 0


def test_no_overflow_within_limit():
    c = HitCounter(limit=10)
    for _ in range(10):
        c.hit()
    assert c.overflow is False
