from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    stage: str
    provider: str
    model: str
    prompt: str
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_seconds: float | None = None


class LLMGateway(Protocol):
    def generate(self, request: LLMRequest) -> str:
        ...
