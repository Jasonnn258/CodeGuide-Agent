# CLI prefix argument is parsed but ignored

The CLI accepts `--prefix`, but `main` never passes it into `render`, so custom greetings are dropped.
