from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    stage: str
    event: str
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)


class TraceStore(Protocol):
    def record(self, event: TraceEvent) -> None:
        ...
