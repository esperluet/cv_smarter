from collections.abc import Iterable

from app.application.errors import (
    ArtifactPersistenceError,
    IngestionFailedError,
    IngestorNotFoundError,
    LowQualityExtractionError,
    RenderingFailedError,
    UnsupportedOutputFormatError,
)
from app.application.services.ocr_policy_strategy import OcrRetryContext, RuleBasedOcrPolicyStrategy
from app.domain.models.document_pipeline import DocumentProcessingResult, IngestionPolicy, IngestionResult, InputDocument
from app.domain.services.artifact_store import ArtifactStore
from app.domain.services.document_ingestor import DocumentIngestor
from app.domain.services.document_renderer import DocumentRenderer
from app.domain.services.ingestion_quality_validator import IngestionQualityValidator


class ProcessDocumentPipelineUseCase:
    def __init__(
        self,
        *,
        ingestors: Iterable[DocumentIngestor],
        renderers: Iterable[DocumentRenderer],
        artifact_store: ArtifactStore,
        quality_validator: IngestionQualityValidator | None = None,
        ocr_policy_strategy: RuleBasedOcrPolicyStrategy | None = None,
    ) -> None:
        self._ingestors = list(ingestors)
        self._renderers = {renderer.output_format: renderer for renderer in renderers}
        self._artifact_store = artifact_store
        self._quality_validator = quality_validator
        self._ocr_policy_strategy = ocr_policy_strategy

    def execute(self, *, source_document: InputDocument, output_formats: Iterable[str]) -> DocumentProcessingResult:
        compatible_ingestors = self._resolve_ingestors(source_document.media_type)
        policy = self._build_initial_policy(source_document)
        ingestion_result, last_error, attempted_engines = self._ingest_with_policy(
            source_document=source_document,
            ingestors=compatible_ingestors,
            policy=policy,
        )

        if ingestion_result is None:
            root_cause = ""
            if last_error is not None:
                root_cause = f" Root cause: {type(last_error).__name__}: {last_error}"
            raise IngestionFailedError(
                f"Document ingestion failed for media type {source_document.media_type} "
                f"with engines: {', '.join(attempted_engines)}.{root_cause}"
            ) from last_error

        report = ingestion_result.report
        final_policy = policy
        if self._quality_validator is not None:
            quality = self._quality_validator.assess(ingestion_result.canonical_document)
            retry_policy = self._build_retry_policy(
                source_document=source_document,
                quality_flags=quality.flags,
                extracted_text=ingestion_result.canonical_document.text,
                previous_policy=policy,
            )
            if not quality.accepted and retry_policy is not None:
                retry_result, retry_last_error, retry_attempts = self._ingest_with_policy(
                    source_document=source_document,
                    ingestors=compatible_ingestors,
                    policy=retry_policy,
                )
                attempted_engines.extend(retry_attempts)
                if retry_result is None:
                    root_cause = ""
                    if retry_last_error is not None:
                        root_cause = f" Root cause: {type(retry_last_error).__name__}: {retry_last_error}"
                    raise IngestionFailedError(
                        f"Document ingestion failed during OCR retry for media type {source_document.media_type} "
                        f"with engines: {', '.join(retry_attempts)}.{root_cause}"
                    ) from retry_last_error
                ingestion_result = retry_result
                report = retry_result.report
                final_policy = retry_policy
                quality = self._quality_validator.assess(ingestion_result.canonical_document)

            report = report.__class__(
                engine_name=report.engine_name,
                engine_version=report.engine_version,
                warnings=list(report.warnings),
                quality_score=quality.score,
                quality_flags=quality.flags,
                engine_attempts=attempted_engines,
            )
            if not quality.accepted:
                raise LowQualityExtractionError(
                    f"Extraction quality check failed: {', '.join(quality.flags) or 'unknown_reason'}"
                )
        else:
            report = report.__class__(
                engine_name=report.engine_name,
                engine_version=report.engine_version,
                warnings=list(report.warnings),
                quality_score=report.quality_score,
                quality_flags=report.quality_flags,
                engine_attempts=attempted_engines,
            )
        report = report.__class__(
            engine_name=report.engine_name,
            engine_version=report.engine_version,
            warnings=[
                *report.warnings,
                f"ocr_policy: enabled={str(final_policy.ocr_enabled).lower()}, reason={final_policy.decision_reason}",
            ],
            quality_score=report.quality_score,
            quality_flags=report.quality_flags,
            engine_attempts=report.engine_attempts,
        )

        artifacts = []
        for output_format in output_formats:
            renderer = self._renderers.get(output_format)
            if renderer is None:
                raise UnsupportedOutputFormatError(f"Unsupported output format: {output_format}")

            try:
                content = renderer.render(ingestion_result.canonical_document)
            except Exception as exc:
                raise RenderingFailedError(f"Rendering failed for format: {output_format}") from exc

            try:
                artifact = self._artifact_store.save_artifact(
                    source_document=source_document,
                    output_format=output_format,
                    media_type=renderer.media_type,
                    content=content,
                )
            except Exception as exc:
                raise ArtifactPersistenceError(f"Failed to persist artifact: {output_format}") from exc

            artifacts.append(artifact)

        return DocumentProcessingResult(
            canonical_document=ingestion_result.canonical_document,
            report=report,
            artifacts=artifacts,
        )

    def _resolve_ingestors(self, media_type: str) -> list[DocumentIngestor]:
        compatible = [ingestor for ingestor in self._ingestors if ingestor.supports(media_type)]
        if not compatible:
            raise IngestorNotFoundError(f"No ingestor registered for media type: {media_type}")
        return compatible

    def _build_initial_policy(self, source_document: InputDocument) -> IngestionPolicy:
        if self._ocr_policy_strategy is None:
            return IngestionPolicy(ocr_enabled=False, decision_reason="no_strategy")
        return self._ocr_policy_strategy.initial_policy(source_document)

    def _build_retry_policy(
        self,
        *,
        source_document: InputDocument,
        quality_flags: list[str],
        extracted_text: str,
        previous_policy: IngestionPolicy,
    ) -> IngestionPolicy | None:
        if self._ocr_policy_strategy is None:
            return None
        return self._ocr_policy_strategy.retry_policy(
            source_document,
            context=OcrRetryContext(
                quality_flags=quality_flags,
                extracted_text=extracted_text,
                previous_policy=previous_policy,
            ),
        )

    def _ingest_with_policy(
        self,
        *,
        source_document: InputDocument,
        ingestors: list[DocumentIngestor],
        policy: IngestionPolicy,
    ) -> tuple[IngestionResult | None, Exception | None, list[str]]:
        ingestion_result = None
        last_error: Exception | None = None
        attempted_engines: list[str] = []
        for ingestor in ingestors:
            attempted_engines.append(
                f"{type(ingestor).__name__}(ocr={'on' if policy.ocr_enabled else 'off'})"
            )
            try:
                ingestion_result = ingestor.ingest(source_document, policy=policy)
                break
            except Exception as exc:
                last_error = exc

        return ingestion_result, last_error, attempted_engines
