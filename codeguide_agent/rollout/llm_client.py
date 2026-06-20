from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from codeguide_agent.rollout.llm_config import LLMConfig


@dataclass(frozen=True)
class LLMResult:
    content: str
    backend: str
    model: str
    status: str = "success"
    error: str = ""
    total_tokens: int = 0

    def safe_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "model": self.model,
            "status": self.status,
            "error": self.error,
            "total_tokens": self.total_tokens,
            "content_preview": self.content[:500],
        }


class LLMClient(Protocol):
    def complete(self, prompt: str) -> LLMResult:
        ...


class MockLLMClient:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = list(responses or [])
        self.call_count = 0

    def complete(self, prompt: str) -> LLMResult:
        self.call_count += 1
        if self.responses:
            content = self.responses.pop(0)
        else:
            content = self._scripted_response()
        return LLMResult(content=content, backend="mock", model="mock-codeguide")

    def _scripted_response(self) -> str:
        sequence = [
            {"action": "repo_tree", "args": {"max_depth": 4}},
            {"action": "search_repo", "args": {"query": "config", "path": "src", "file_glob": "*.py"}},
            {"action": "read_file", "args": {"file_path": "src/config_loader.py"}},
            {"action": "stop", "args": {"reason": "mock_llm_complete"}},
        ]
        index = min(self.call_count - 1, len(sequence) - 1)
        return json.dumps(sequence[index])


class OpenAICompatibleClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.call_count = 0

    def complete(self, prompt: str) -> LLMResult:
        self.call_count += 1
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return LLMResult(
                content="",
                backend=self.config.backend,
                model=self.config.model,
                status="error",
                error=str(exc),
            )
        choice = (data.get("choices") or [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return LLMResult(
            content=content,
            backend=self.config.backend,
            model=self.config.model,
            total_tokens=int(usage.get("total_tokens", 0) or 0),
        )


def make_llm_client(config: LLMConfig) -> LLMClient:
    if config.mock or config.backend == "mock":
        return MockLLMClient()
    if config.backend == "openai_compatible" and config.available:
        return OpenAICompatibleClient(config)
    return MockLLMClient(responses=[json.dumps({"action": "stop", "args": {"reason": config.skip_reason}})])
