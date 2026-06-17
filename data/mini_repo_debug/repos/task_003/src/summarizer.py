from __future__ import annotations

import csv
from io import StringIO


def total_amount(csv_text: str) -> int:
    reader = csv.DictReader(StringIO(csv_text))
    total = 0
    for row in reader:
        total += int(row["amount"])
    return total
