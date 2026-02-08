import re
from datetime import UTC, datetime

from app.application.dto.cv_pdf_result import CvPdfResult
from app.application.errors import CvExportError
from app.application.use_cases.export_cv_pdf import ExportCvPdfUseCase
from app.application.use_cases.generate_targeted_cv_from_source import GenerateTargetedCvFromSourceUseCase


class GenerateTargetedCvPdfFromSourceUseCase:
    def __init__(
        self,
        *,
        generator: GenerateTargetedCvFromSourceUseCase,
        exporter: ExportCvPdfUseCase,
    ) -> None:
        self._generator = generator
        self._exporter = exporter

    def execute(
        self,
        *,
        user_id: str,
        source_id: str,
        job_description: str,
        graph_id: str | None = None,
        format_hint: str | None = None,
    ) -> CvPdfResult:
        generation = self._generator.execute(
            user_id=user_id,
            source_id=source_id,
            job_description=job_description,
            graph_id=graph_id,
        )

        final_cv = generation.generation_result.final_cv.strip()
        if not final_cv:
            raise CvExportError("Final CV content is empty and cannot be exported")

        safe_name = _slugify(generation.source.name)
        date_fragment = datetime.now(UTC).strftime("%Y%m%d")
        filename = f"{safe_name}_{date_fragment}.pdf"

        export_result = self._exporter.execute(
            content=final_cv,
            format_hint=format_hint or "markdown",
            filename=filename,
        )

        return CvPdfResult(
            filename=export_result.filename,
            content_bytes=export_result.content_bytes,
            media_type=export_result.media_type,
            run_id=generation.generation_result.run_id,
        )


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return "cv"

    normalized = re.sub(r"[^a-z0-9]+", "_", lowered)
    normalized = normalized.strip("_")
    return normalized or "cv"
