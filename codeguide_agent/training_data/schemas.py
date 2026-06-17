from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SYSTEM_MESSAGE = "You are CodeGuide-Agent, a repo-level code repair agent."


@dataclass
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class SFTSample:
    messages: list[ChatMessage]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"messages": [message.to_dict() for message in self.messages], "metadata": self.metadata}
