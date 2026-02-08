from app.application.dto.ground_source_result import CvGenerationFromSourceResult
from app.application.errors import GroundSourceNotFoundError, InvalidJobDescriptionError
from app.domain.repositories.ground_source_repository import GroundSourceRepository
from app.domain.services.cv_generation_orchestrator import CvGenerationOrchestrator


class GenerateTargetedCvFromSourceUseCase:
    def __init__(
        self,
        *,
        sources: GroundSourceRepository,
        orchestrator: CvGenerationOrchestrator,
        max_job_description_chars: int = 12000,
    ) -> None:
        self._sources = sources
        self._orchestrator = orchestrator
        self._max_job_description_chars = max_job_description_chars

    def execute(
        self,
        *,
        user_id: str,
        source_id: str,
        job_description: str,
        graph_id: str | None = None,
    ) -> CvGenerationFromSourceResult:
        source = self._sources.get_for_user(source_id=source_id, user_id=user_id)
        if source is None:
            raise GroundSourceNotFoundError("Ground source not found")

        normalized_job_description = job_description.strip()
        if not normalized_job_description:
            raise InvalidJobDescriptionError("Job description is required")
        if len(normalized_job_description) > self._max_job_description_chars:
            raise InvalidJobDescriptionError(
                f"Job description is too long (max {self._max_job_description_chars} characters)"
            )

        generation_result = self._orchestrator.generate(
            cv_text=source.canonical_text,
            job_description=normalized_job_description,
            graph_id=graph_id,
        )

        return CvGenerationFromSourceResult(
            source=source,
            generation_result=generation_result,
        )
