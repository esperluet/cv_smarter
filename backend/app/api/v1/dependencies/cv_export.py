from functools import lru_cache

from app.application.use_cases.export_cv_pdf import ExportCvPdfUseCase
from app.infrastructure.rendering.markdown_pdf_exporter import MarkdownPdfExporter


@lru_cache(maxsize=1)
def get_cv_pdf_exporter() -> MarkdownPdfExporter:
    return MarkdownPdfExporter()


@lru_cache(maxsize=1)
def get_export_cv_pdf_use_case() -> ExportCvPdfUseCase:
    return ExportCvPdfUseCase(exporter=get_cv_pdf_exporter())
