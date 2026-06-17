from __future__ import annotations

import argparse


def transform(text: str, uppercase: bool = False) -> str:
    if uppercase:
        return text
    return text.lower()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--uppercase", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(transform(args.text, uppercase=args.uppercase))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
