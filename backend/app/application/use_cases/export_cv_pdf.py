from app.application.dto.cv_pdf_result import CvPdfResult
from app.application.errors import CvExportError
from app.domain.services.cv_exporter import CvExporter


class ExportCvPdfUseCase:
    def __init__(self, *, exporter: CvExporter) -> None:
        self._exporter = exporter

    def execute(
        self,
        *,
        content: str,
        format_hint: str | None = None,
        filename: str = "cv_export.pdf",
    ) -> CvPdfResult:
        normalized_content = content.strip()
        if not normalized_content:
            raise CvExportError("Content is required to export PDF")

        normalized_filename = filename.strip() or "cv_export.pdf"
        if not normalized_filename.lower().endswith(".pdf"):
            normalized_filename = f"{normalized_filename}.pdf"

        pdf_bytes = self._exporter.render_pdf(
            content=normalized_content,
            format_hint=format_hint,
        )

        if not pdf_bytes:
            raise CvExportError("Generated PDF is empty")

        return CvPdfResult(
            filename=normalized_filename,
            content_bytes=pdf_bytes,
        )
