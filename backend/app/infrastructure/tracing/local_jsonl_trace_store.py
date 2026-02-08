import json
from pathlib import Path

from app.domain.services.trace_store import TraceEvent, TraceStore


class LocalJsonlTraceStore(TraceStore):
    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def record(self, event: TraceEvent) -> None:
        path = self._base_dir / f"{event.run_id}.jsonl"
        payload = {
            "run_id": event.run_id,
            "stage": event.stage,
            "event": event.event,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
