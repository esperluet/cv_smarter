from dataclasses import dataclass

from app.domain.models.document_pipeline import ProcessingReport, RenderedArtifact


@dataclass(frozen=True)
class CVAnalysis:
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    metrics: dict[str, int]
    artifacts: list[RenderedArtifact]
    processing_report: ProcessingReport | None = None
