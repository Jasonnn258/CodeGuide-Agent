# Dict lookup is case-sensitive instead of case-insensitive

`case_insensitive_get` should find values regardless of key casing, so `"Host"` and `"host"` retrieve the same entry.
