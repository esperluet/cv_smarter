from dataclasses import dataclass

from app.domain.models.document_pipeline import DocumentProcessingResult


@dataclass(frozen=True)
class DocumentUploadResult:
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    processing_result: DocumentProcessingResult
