from __future__ import annotations

import argparse


def transform(text: str, mode: str = "upper") -> str:
    if mode == "upper":
        return text.upper()
    elif mode == "lower":
        return text.lower()
    return text


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--mode", default="upper", choices=["upper", "lower"])
    args = parser.parse_args(argv)
    return transform(args.text, mode="upper")
