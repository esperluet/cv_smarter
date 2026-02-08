from pydantic import BaseModel, Field

from app.api.v1.schemas.cv import ArtifactResponse, ProcessingReportResponse


class CanonicalDocumentResponse(BaseModel):
    schema_version: str
    source_media_type: str
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentProcessResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    canonical_document: CanonicalDocumentResponse
    processing_report: ProcessingReportResponse
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
