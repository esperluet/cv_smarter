from typing import Protocol

from app.domain.models.cv_generation import CvGenerationResult


class CvGenerationOrchestrator(Protocol):
    def generate(
        self,
        *,
        cv_text: str,
        job_description: str,
        graph_id: str | None = None,
    ) -> CvGenerationResult:
        ...
