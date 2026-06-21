# Locale-specific greetings reuse the wrong cache entry

The greeting cache returns the first locale seen for a user id. It should cache by both user id and locale.
