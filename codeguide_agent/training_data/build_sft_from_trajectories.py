"""LEGACY COMPATIBILITY MODULE.

The canonical CodeGuide-Agent training data pipeline is:

    codeguide_agent.dataset.export_training_candidates
    codeguide_agent.dataset.prepare_training_package
    codeguide_agent.training.build_hf_training_data

This module is kept for older Phase-2 tests and compatibility only.
Do not use it as the public SFT data entrypoint.
"""

from __future__ import annotations

"""Deprecated compatibility wrapper for the canonical SFT builder.

Use `python -m codeguide_agent.data_builders.build_sft` and import
`codeguide_agent.data_builders.build_sft` in new code.
"""

from codeguide_agent.data_builders.build_sft import build_sample, build_sft_dataset, main, read_trajectory

__all__ = ["build_sample", "build_sft_dataset", "main", "read_trajectory"]


if __name__ == "__main__":
    raise SystemExit(main())
