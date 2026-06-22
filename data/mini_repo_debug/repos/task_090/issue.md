# CLI repeat command ignores --count

The CLI accepts `--count N`, but `main` always passes `count=1` to `repeat`, so the text is never actually repeated.
