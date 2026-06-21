from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--uppercase", action="store_true")
    parser.add_argument("name")
    return parser


def render(name: str, limit: int = 10, uppercase: bool = False) -> str:
    value = name.upper() if uppercase else name
    return f"{value}:{limit}"


def main(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    return render(args.name)
