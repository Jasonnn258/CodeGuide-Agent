# CLI flags are parsed but ignored

The small CLI helper parses `--limit` and `--uppercase`, but callers report that those options do not affect the rendered output.

Please propagate parsed arguments into the rendering layer while preserving the public function names.
