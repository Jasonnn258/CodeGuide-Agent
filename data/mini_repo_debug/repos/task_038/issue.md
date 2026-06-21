# Adding a tag should be idempotent

`ensure_tag` should add a missing tag while preserving existing order. Re-adding an existing tag should not duplicate it or mutate the input list.
