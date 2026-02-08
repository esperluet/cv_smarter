from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PromptTemplate:
    prompt_id: str
    content: str
    version: str
    sha256: str


class PromptRepository(Protocol):
    def get(self, prompt_id: str) -> PromptTemplate:
        ...
