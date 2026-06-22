from __future__ import annotations

import argparse


def repeat(text: str, count: int = 1, sep: str = " ") -> str:
    return sep.join([text] * count)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--sep", default=" ")
    args = parser.parse_args(argv)
    return repeat(args.text, count=1, sep=args.sep)
