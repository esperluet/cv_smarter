from pydantic import BaseModel, Field


class ArtifactResponse(BaseModel):
    format: str
    media_type: str
    storage_path: str
    download_token: str | None = None
    download_url: str | None = None


class ProcessingReportResponse(BaseModel):
    engine_name: str
    engine_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    quality_score: float | None = None
    quality_flags: list[str] = Field(default_factory=list)
    engine_attempts: list[str] = Field(default_factory=list)


class CVUploadResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    metrics: dict[str, int] = Field(default_factory=dict)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    processing_report: ProcessingReportResponse | None = None
