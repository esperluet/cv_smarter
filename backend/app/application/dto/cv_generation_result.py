from dataclasses import dataclass

from app.domain.models.cv_generation import CvGenerationResult
from app.domain.models.document_pipeline import ProcessingReport


@dataclass(frozen=True)
class CvGenerationUploadResult:
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    processing_report: ProcessingReport
    generation_result: CvGenerationResult
