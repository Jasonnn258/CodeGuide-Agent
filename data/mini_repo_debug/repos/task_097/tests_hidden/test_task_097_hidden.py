from task_097_lib.limiter import RateLimiter


def test_blocked_count_increments():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    rl.allow()
    rl.allow()
    rl.allow()
    assert rl._blocked_count == 2


def test_reset_clears_blocked_count():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    rl.allow()
    rl.allow()
    rl.reset()
    assert rl._blocked_count == 0
