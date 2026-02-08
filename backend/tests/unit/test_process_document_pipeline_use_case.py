from pathlib import Path

import pytest

from app.application.errors import IngestionFailedError, IngestorNotFoundError, LowQualityExtractionError, UnsupportedOutputFormatError
from app.application.services.ocr_policy_strategy import RuleBasedOcrPolicyStrategy
from app.application.use_cases.process_document_pipeline import ProcessDocumentPipelineUseCase
from app.domain.models.document_pipeline import (
    CanonicalDocument,
    IngestionResult,
    IngestionPolicy,
    InputDocument,
    ProcessingReport,
    RenderedArtifact,
)
from app.domain.services.ingestion_quality_validator import IngestionQualityAssessment


class FakeIngestor:
    def __init__(self, supported_media_types: set[str]) -> None:
        self.supported_media_types = supported_media_types

    def supports(self, media_type: str) -> bool:
        return media_type in self.supported_media_types

    def ingest(self, document: InputDocument, *, policy: IngestionPolicy | None = None) -> IngestionResult:
        canonical = CanonicalDocument(
            schema_version="1.0",
            source_media_type=document.media_type,
            text="Hello",
            metadata={"original_name": document.original_name},
        )
        report = ProcessingReport(engine_name="fake", engine_version="1")
        return IngestionResult(canonical_document=canonical, report=report)


class FakeRenderer:
    def __init__(self, output_format: str, media_type: str) -> None:
        self._output_format = output_format
        self._media_type = media_type

    @property
    def output_format(self) -> str:
        return self._output_format

    @property
    def media_type(self) -> str:
        return self._media_type

    def render(self, document: CanonicalDocument) -> str:
        return f"{self._output_format}:{document.text}"


class FakeArtifactStore:
    def save_artifact(
        self,
        *,
        source_document: InputDocument,
        output_format: str,
        media_type: str,
        content: str,
    ) -> RenderedArtifact:
        return RenderedArtifact(
            format=output_format,
            media_type=media_type,
            storage_path=f"/tmp/{Path(source_document.original_name).stem}.{output_format}",
        )


class FakeQualityValidator:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted

    def assess(self, document: CanonicalDocument) -> IngestionQualityAssessment:
        if self.accepted:
            return IngestionQualityAssessment(accepted=True, score=0.95, flags=[])
        return IngestionQualityAssessment(accepted=False, score=0.1, flags=["pdf_internal_markers"])


def test_pipeline_success() -> None:
    use_case = ProcessDocumentPipelineUseCase(
        ingestors=[FakeIngestor({"application/pdf"})],
        renderers=[
            FakeRenderer("markdown", "text/markdown"),
            FakeRenderer("json", "application/json"),
        ],
        artifact_store=FakeArtifactStore(),
    )

    result = use_case.execute(
        source_document=InputDocument(
            source_path=Path("/tmp/resume.pdf"),
            original_name="resume.pdf",
            media_type="application/pdf",
        ),
        output_formats=("markdown", "json"),
    )

    assert result.report.engine_name == "fake"
    assert result.report.engine_attempts == ["FakeIngestor(ocr=off)"]
    assert [artifact.format for artifact in result.artifacts] == ["markdown", "json"]


def test_pipeline_fails_when_ingestor_missing() -> None:
    use_case = ProcessDocumentPipelineUseCase(
        ingestors=[FakeIngestor({"text/plain"})],
        renderers=[FakeRenderer("markdown", "text/markdown")],
        artifact_store=FakeArtifactStore(),
    )

    with pytest.raises(IngestorNotFoundError):
        use_case.execute(
            source_document=InputDocument(
                source_path=Path("/tmp/resume.pdf"),
                original_name="resume.pdf",
                media_type="application/pdf",
            ),
            output_formats=("markdown",),
        )


def test_pipeline_fails_when_output_format_missing() -> None:
    use_case = ProcessDocumentPipelineUseCase(
        ingestors=[FakeIngestor({"application/pdf"})],
        renderers=[FakeRenderer("markdown", "text/markdown")],
        artifact_store=FakeArtifactStore(),
    )

    with pytest.raises(UnsupportedOutputFormatError):
        use_case.execute(
            source_document=InputDocument(
                source_path=Path("/tmp/resume.pdf"),
                original_name="resume.pdf",
                media_type="application/pdf",
            ),
            output_formats=("json",),
        )


def test_pipeline_fails_when_all_ingestors_fail() -> None:
    class FailingIngestor(FakeIngestor):
        def ingest(self, document: InputDocument, *, policy: IngestionPolicy | None = None) -> IngestionResult:
            raise RuntimeError("boom")

    use_case = ProcessDocumentPipelineUseCase(
        ingestors=[FailingIngestor({"application/pdf"})],
        renderers=[FakeRenderer("json", "application/json")],
        artifact_store=FakeArtifactStore(),
    )

    with pytest.raises(IngestionFailedError):
        use_case.execute(
            source_document=InputDocument(
                source_path=Path("/tmp/resume.pdf"),
                original_name="resume.pdf",
                media_type="application/pdf",
            ),
            output_formats=("json",),
        )


def test_pipeline_fails_quality_gate() -> None:
    use_case = ProcessDocumentPipelineUseCase(
        ingestors=[FakeIngestor({"application/pdf"})],
        renderers=[FakeRenderer("json", "application/json")],
        artifact_store=FakeArtifactStore(),
        quality_validator=FakeQualityValidator(accepted=False),
    )

    with pytest.raises(LowQualityExtractionError):
        use_case.execute(
            source_document=InputDocument(
                source_path=Path("/tmp/resume.pdf"),
                original_name="resume.pdf",
                media_type="application/pdf",
            ),
            output_formats=("json",),
        )


def test_pipeline_retries_with_ocr_when_quality_fails() -> None:
    class OcrAwareIngestor(FakeIngestor):
        def ingest(self, document: InputDocument, *, policy: IngestionPolicy | None = None) -> IngestionResult:
            ocr_on = bool(policy and policy.ocr_enabled)
            text = "ok extracted text from resume" if ocr_on else "%PDF- stream endstream endobj xref"
            canonical = CanonicalDocument(
                schema_version="1.0",
                source_media_type=document.media_type,
                text=text,
                metadata={"original_name": document.original_name},
            )
            return IngestionResult(
                canonical_document=canonical,
                report=ProcessingReport(engine_name="ocr-aware", engine_version="1"),
            )

    class OcrRetryQualityValidator:
        def assess(self, document: CanonicalDocument) -> IngestionQualityAssessment:
            if "%PDF-" in document.text:
                return IngestionQualityAssessment(accepted=False, score=0.0, flags=["pdf_internal_markers"])
            return IngestionQualityAssessment(accepted=True, score=0.95, flags=[])

    use_case = ProcessDocumentPipelineUseCase(
        ingestors=[OcrAwareIngestor({"application/pdf"})],
        renderers=[FakeRenderer("json", "application/json")],
        artifact_store=FakeArtifactStore(),
        quality_validator=OcrRetryQualityValidator(),
        ocr_policy_strategy=RuleBasedOcrPolicyStrategy(default_ocr_enabled=False, auto_retry_on_quality_failure=True),
    )

    result = use_case.execute(
        source_document=InputDocument(
            source_path=Path("/tmp/resume.pdf"),
            original_name="resume.pdf",
            media_type="application/pdf",
        ),
        output_formats=("json",),
    )

    assert result.canonical_document.text == "ok extracted text from resume"
    assert result.report.engine_attempts == [
        "OcrAwareIngestor(ocr=off)",
        "OcrAwareIngestor(ocr=on)",
    ]
