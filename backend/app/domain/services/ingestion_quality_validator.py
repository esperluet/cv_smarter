from dataclasses import dataclass, field
from typing import Protocol

from app.domain.models.document_pipeline import CanonicalDocument


@dataclass(frozen=True)
class IngestionQualityAssessment:
    accepted: bool
    score: float
    flags: list[str] = field(default_factory=list)


class IngestionQualityValidator(Protocol):
    def assess(self, document: CanonicalDocument) -> IngestionQualityAssessment:
        ...
