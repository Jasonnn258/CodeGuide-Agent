from __future__ import annotations

import argparse


def render(name: str, prefix: str = "Hello") -> str:
    return f"{prefix}, {name}!"


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--prefix", default="Hello")
    args = parser.parse_args(argv)
    return render(args.name)
