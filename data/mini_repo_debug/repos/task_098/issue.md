# ensure_seeded silently ignores conflicting seeds

`ensure_seeded` should raise `RuntimeError` if called with a different seed after the first successful call, so that accidental re-seeding with a conflicting value is caught.
