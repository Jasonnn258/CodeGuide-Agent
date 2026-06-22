# Cache key ignores argument types

`make_cache_key` should produce different keys for values that compare equal but have different types, such as the integer `1` and the float `1.0`.
