from __future__ import annotations

import os

from codeguide_agent.runtime.llm.base import LLMBackend, MockBackend


def get_backend(name: str | None = None) -> LLMBackend:
    """Return a backend. External providers are intentionally deferred in v0."""
    requested = name or os.environ.get("CODEGUIDE_LLM_BACKEND", "mock")
    if requested != "mock" and not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        return MockBackend()
    return MockBackend()
