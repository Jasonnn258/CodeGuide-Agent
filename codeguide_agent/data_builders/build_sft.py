from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SFT examples from CodeGuide trajectories.")
    parser.add_argument("--input", required=True, help="Input trajectory JSONL directory or file")
    parser.add_argument("--output", required=True, help="Output SFT JSONL path")
    args = parser.parse_args()
    raise SystemExit(f"SFT builder skeleton only; requested input={args.input} output={args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
