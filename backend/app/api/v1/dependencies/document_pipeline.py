from functools import lru_cache

from app.application.services.ocr_policy_strategy import RuleBasedOcrPolicyStrategy
from app.application.use_cases.process_document_pipeline import ProcessDocumentPipelineUseCase
from app.core.settings import settings
from app.domain.services.document_ingestor import DocumentIngestor
from app.infrastructure.ingestion.docling_document_ingestor import DoclingDocumentIngestor
from app.infrastructure.ingestion.fallback_text_document_ingestor import FallbackTextDocumentIngestor
from app.infrastructure.ingestion.basic_ingestion_quality_validator import BasicIngestionQualityValidator
from app.infrastructure.rendering.json_renderer import JsonRenderer
from app.infrastructure.rendering.markdown_renderer import MarkdownRenderer
from app.infrastructure.storage.local_artifact_store import LocalArtifactStore


@lru_cache(maxsize=1)
def get_document_pipeline_use_case() -> ProcessDocumentPipelineUseCase:
    return ProcessDocumentPipelineUseCase(
        ingestors=resolve_ingestors(),
        renderers=[MarkdownRenderer(), JsonRenderer()],
        artifact_store=LocalArtifactStore(base_dir=settings.artifact_dir),
        quality_validator=BasicIngestionQualityValidator(),
        ocr_policy_strategy=RuleBasedOcrPolicyStrategy(
            default_ocr_enabled=settings.document_pdf_do_ocr,
            auto_retry_on_quality_failure=settings.document_ocr_auto_retry_on_quality_failure,
            retry_min_text_length=settings.document_ocr_retry_min_text_length,
        ),
    )


def resolve_output_formats() -> tuple[str, ...]:
    raw = settings.document_output_formats
    values = [item.strip() for item in raw.split(",")]
    normalized = tuple(item for item in values if item)
    if not normalized:
        return ("markdown", "json")
    return normalized


def resolve_ingestors() -> list[DocumentIngestor]:
    docling = DoclingDocumentIngestor(enable_pdf_ocr=settings.document_pdf_do_ocr)
    fallback = FallbackTextDocumentIngestor()

    if settings.document_ingestor_preferred == "docling":
        return [docling, fallback]
    return [fallback, docling]
