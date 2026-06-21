# JSON config parser treats string false as enabled

`is_enabled` should support boolean values and common string values, but the string `"false"` must not become true just because it is non-empty.
