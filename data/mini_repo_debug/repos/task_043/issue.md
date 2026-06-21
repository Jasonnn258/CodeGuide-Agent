# Cache keys ignore keyword arguments

`make_cache_key` should produce different keys when keyword arguments differ, while remaining stable when kwargs are supplied in a different order.
