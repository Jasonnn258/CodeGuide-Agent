# Blank JSONL lines crash parsing

JSON Lines exports can include blank spacer lines. The loader should skip blank lines and keep parsing valid records.
