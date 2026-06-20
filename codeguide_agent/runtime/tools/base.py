from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from codeguide_agent.runtime.agent.types import Observation, ObservationStatus


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    timed_out: bool = False

    def to_observation(self, tool_name: str) -> Observation:
        if self.timed_out:
            status = ObservationStatus.TIMEOUT
        else:
            status = ObservationStatus.SUCCESS if self.success else ObservationStatus.ERROR
        return Observation(status=status, output=self.output, tool_name=tool_name, error=self.error)


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> "ToolRegistry":
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return self

    def execute(self, name: str, params: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools)) or "none"
            return ToolResult(False, "", f"unknown tool {name!r}; available: {available}")
        try:
            return tool.execute(params)
        except Exception as exc:
            return ToolResult(False, "", f"tool {name!r} raised: {exc}")

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)
