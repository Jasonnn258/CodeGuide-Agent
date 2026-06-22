from __future__ import annotations


def word_freq(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    while words:
        w = words.pop()
        counts[w] = counts.get(w, 0) + 1
    return counts
