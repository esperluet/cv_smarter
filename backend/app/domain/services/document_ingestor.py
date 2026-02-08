from typing import Protocol

from app.domain.models.document_pipeline import IngestionPolicy, IngestionResult, InputDocument


class DocumentIngestor(Protocol):
    def supports(self, media_type: str) -> bool:
        ...

    def ingest(self, document: InputDocument, *, policy: IngestionPolicy | None = None) -> IngestionResult:
        ...
