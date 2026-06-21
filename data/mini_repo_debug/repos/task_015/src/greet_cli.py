from __future__ import annotations

import argparse


def build_message(name: str, excited: bool = False) -> str:
    message = f"Hello, {name}"
    if excited:
        return message + "!"
    return message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--excited", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(build_message(args.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
