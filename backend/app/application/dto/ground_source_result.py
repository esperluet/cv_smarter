from dataclasses import dataclass

from app.domain.models.cv_generation import CvGenerationResult
from app.domain.models.document_pipeline import ProcessingReport
from app.domain.models.ground_source import GroundSource


@dataclass(frozen=True)
class GroundSourceCreateResult:
    source: GroundSource
    processing_report: ProcessingReport


@dataclass(frozen=True)
class CvGenerationFromSourceResult:
    source: GroundSource
    generation_result: CvGenerationResult
