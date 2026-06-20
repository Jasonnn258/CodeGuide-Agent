from __future__ import annotations

"""Deprecated compatibility wrapper for the canonical SFT builder.

Use `python -m codeguide_agent.data_builders.build_sft` and import
`codeguide_agent.data_builders.build_sft` in new code.
"""

from codeguide_agent.data_builders.build_sft import build_sample, build_sft_dataset, main, read_trajectory

__all__ = ["build_sample", "build_sft_dataset", "main", "read_trajectory"]


if __name__ == "__main__":
    raise SystemExit(main())
