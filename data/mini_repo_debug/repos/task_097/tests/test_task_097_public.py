from task_097_lib.limiter import RateLimiter


def test_allows_within_limit():
    rl = RateLimiter(max_calls=3, window_seconds=60)
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is True


def test_blocks_over_limit():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    assert rl.allow() is True
    assert rl.allow() is False


def test_reset_clears_window():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    rl.allow()
    rl.reset()
    assert rl.allow() is True
