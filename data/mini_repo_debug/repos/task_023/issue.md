# Build parameter-sensitive cache keys

The cache key helper is used by a small service wrapper.

Different calls with different parameters should not collide. The current helper is too coarse and can reuse stale results across different inputs.

Please make the key stable and parameter-sensitive.
