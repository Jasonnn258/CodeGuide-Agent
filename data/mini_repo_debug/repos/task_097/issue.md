# RateLimiter does not track blocked requests

`RateLimiter` should count how many requests have been blocked due to rate limiting. The counter must reset when `reset()` is called.
