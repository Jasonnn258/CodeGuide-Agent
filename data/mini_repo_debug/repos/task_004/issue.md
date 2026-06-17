# Region-specific prices leak through cache

Fetching the same item in different regions can return the first region's value. The cache should distinguish item and region.
