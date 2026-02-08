from app.domain.models.document_pipeline import CanonicalDocument, IngestionPolicy, IngestionResult, InputDocument, ProcessingReport


class FallbackTextDocumentIngestor:
    def __init__(self, supported_media_types: set[str] | None = None) -> None:
        default_media_types = {"text/plain"}
        self._supported_media_types = supported_media_types or default_media_types

    def supports(self, media_type: str) -> bool:
        return media_type in self._supported_media_types

    def ingest(self, document: InputDocument, *, policy: IngestionPolicy | None = None) -> IngestionResult:
        payload = document.source_path.read_bytes()
        text = payload.decode("utf-8", errors="ignore")
        warnings = []
        if not text.strip():
            warnings.append("Fallback ingestion produced empty or low-quality text")

        canonical_document = CanonicalDocument(
            schema_version="1.0",
            source_media_type=document.media_type,
            text=text,
            metadata={"original_name": document.original_name},
        )
        report = ProcessingReport(
            engine_name="fallback_text",
            engine_version="1",
            warnings=warnings,
        )
        return IngestionResult(canonical_document=canonical_document, report=report)
