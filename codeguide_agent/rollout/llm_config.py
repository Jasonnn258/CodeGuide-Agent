from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    backend: str = "mock"
    model: str = "mock-codeguide"
    base_url: str = ""
    api_key: str = ""
    timeout: int = 30
    max_tokens: int = 512
    temperature: float = 0.0
    budget_usd: float = 0.0
    max_calls_per_task: int = 6
    max_concurrency: int = 1
    qps_limit: float = 1.0
    dry_run: bool = False
    mock: bool = True

    @classmethod
    def from_env(cls) -> "LLMConfig":
        backend = os.environ.get("CODEGUIDE_LLM_BACKEND", "").strip()
        mock = _bool_env("CODEGUIDE_LLM_MOCK", default=not bool(backend))
        if mock:
            backend = "mock"
        elif not backend:
            backend = "openai_compatible"
        return cls(
            backend=backend,
            model=os.environ.get("CODEGUIDE_LLM_MODEL", "mock-codeguide" if backend == "mock" else ""),
            base_url=os.environ.get("CODEGUIDE_LLM_BASE_URL", ""),
            api_key=os.environ.get("CODEGUIDE_LLM_API_KEY", ""),
            timeout=_int_env("CODEGUIDE_LLM_TIMEOUT", 30),
            max_tokens=_int_env("CODEGUIDE_LLM_MAX_TOKENS", 512),
            temperature=_float_env("CODEGUIDE_LLM_TEMPERATURE", 0.0),
            budget_usd=_float_env("CODEGUIDE_LLM_BUDGET_USD", 0.0),
            max_calls_per_task=_int_env("CODEGUIDE_LLM_MAX_CALLS_PER_TASK", 6),
            max_concurrency=_int_env("CODEGUIDE_LLM_MAX_CONCURRENCY", 1),
            qps_limit=_float_env("CODEGUIDE_LLM_QPS_LIMIT", 1.0),
            dry_run=_bool_env("CODEGUIDE_LLM_DRY_RUN", False),
            mock=mock or backend == "mock",
        )

    @property
    def available(self) -> bool:
        if self.mock or self.backend == "mock":
            return True
        if self.backend == "openai_compatible":
            return bool(self.base_url and self.api_key and self.model)
        return False

    @property
    def availability_label(self) -> str:
        if self.mock or self.backend == "mock":
            return "mock"
        return "available" if self.available else "skipped"

    @property
    def skip_reason(self) -> str:
        if self.available:
            return ""
        if self.backend != "openai_compatible":
            return f"unsupported_llm_backend:{self.backend}"
        missing = []
        if not self.base_url:
            missing.append("CODEGUIDE_LLM_BASE_URL")
        if not self.api_key:
            missing.append("CODEGUIDE_LLM_API_KEY")
        if not self.model:
            missing.append("CODEGUIDE_LLM_MODEL")
        return "missing_" + "_".join(missing)

    def safe_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": "<redacted>" if self.api_key else "",
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "budget_usd": self.budget_usd,
            "max_calls_per_task": self.max_calls_per_task,
            "max_concurrency": self.max_concurrency,
            "qps_limit": self.qps_limit,
            "dry_run": self.dry_run,
            "mock": self.mock,
        }


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default
