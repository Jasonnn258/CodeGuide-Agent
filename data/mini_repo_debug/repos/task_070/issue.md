# CLI mode flag is parsed but hard-coded to upper

The CLI accepts `--mode lower`, but `main` always passes `mode="upper"` to `transform`, ignoring the user's choice.
