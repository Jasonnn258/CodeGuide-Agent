# Enrich function hard-codes the ID key

`enrich` should accept an optional `id_key` parameter so callers can specify which field holds the lookup identifier (e.g., `"user_id"` instead of `"id"`).
