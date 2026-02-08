from io import BytesIO
from pathlib import Path

import pytest

from app.application.errors import InvalidJobDescriptionError, MissingFileNameError, UploadedFileTooLargeError
from app.application.use_cases.generate_targeted_cv import GenerateTargetedCvUseCase
from app.domain.models.cv_generation import CvGenerationResult, OrientationDecision
from app.domain.models.document_pipeline import CanonicalDocument, DocumentProcessingResult, ProcessingReport
from app.domain.services.file_storage import FileTooLargeError


class FakeStorage:
    def __init__(self, too_large: bool = False) -> None:
        self.too_large = too_large
        self.deleted_paths: list[str] = []

    def save_from_stream(self, *, stream, original_name: str, content_type: str, max_size_bytes: int):
        if self.too_large:
            raise FileTooLargeError("too_large")

        payload = stream.read()
        return type(
            "StoredFile",
            (),
            {
                "original_name": original_name,
                "content_type": content_type,
                "size_bytes": len(payload),
                "storage_path": Path("/tmp/input.txt"),
            },
        )

    def delete(self, *, storage_path: str) -> None:
        self.deleted_paths.append(storage_path)


class FakePipeline:
    def execute(self, *, source_document, output_formats):
        assert output_formats == ()
        return DocumentProcessingResult(
            canonical_document=CanonicalDocument(
                schema_version="1.0",
                source_media_type=source_document.media_type,
                text="source cv text",
            ),
            report=ProcessingReport(engine_name="fake_ingestor", engine_version="1"),
            artifacts=[],
        )


class FakeOrchestrator:
    def generate(self, *, cv_text: str, job_description: str, graph_id: str | None = None) -> CvGenerationResult:
        assert cv_text == "source cv text"
        assert job_description == "Data platform architect"
        assert graph_id in {None, "cv_rewrite_v1"}
        return CvGenerationResult(
            run_id="run_123",
            graph_id="cv_rewrite_v1",
            graph_version="1",
            final_cv="final cv",
            orientation=OrientationDecision(
                ats_weight=0.4,
                recruiter_weight=0.3,
                technical_weight=0.3,
                rationale="balanced",
            ),
        )


class FailingOrchestrator:
    def generate(self, *, cv_text: str, job_description: str, graph_id: str | None = None) -> CvGenerationResult:
        raise RuntimeError("orchestrator failed")


def test_generate_targeted_cv_use_case_success() -> None:
    use_case = GenerateTargetedCvUseCase(
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        orchestrator=FakeOrchestrator(),
    )

    result = use_case.execute(
        filename="resume.txt",
        content_type="text/plain",
        stream=BytesIO(b"hello"),
        job_description="Data platform architect",
    )

    assert result.filename == "resume.txt"
    assert result.generation_result.run_id == "run_123"
    assert result.generation_result.final_cv == "final cv"


def test_generate_targeted_cv_use_case_rejects_missing_filename() -> None:
    use_case = GenerateTargetedCvUseCase(
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        orchestrator=FakeOrchestrator(),
    )

    with pytest.raises(MissingFileNameError):
        use_case.execute(
            filename=None,
            content_type="text/plain",
            stream=BytesIO(b"x"),
            job_description="Data platform architect",
        )


def test_generate_targeted_cv_use_case_rejects_empty_job_description() -> None:
    use_case = GenerateTargetedCvUseCase(
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        orchestrator=FakeOrchestrator(),
    )

    with pytest.raises(InvalidJobDescriptionError):
        use_case.execute(
            filename="resume.txt",
            content_type="text/plain",
            stream=BytesIO(b"x"),
            job_description="   ",
        )


def test_generate_targeted_cv_use_case_rejects_too_large_upload() -> None:
    use_case = GenerateTargetedCvUseCase(
        storage=FakeStorage(too_large=True),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        orchestrator=FakeOrchestrator(),
    )

    with pytest.raises(UploadedFileTooLargeError):
        use_case.execute(
            filename="resume.txt",
            content_type="text/plain",
            stream=BytesIO(b"x"),
            job_description="Data platform architect",
        )


def test_generate_targeted_cv_use_case_forwards_graph_id() -> None:
    use_case = GenerateTargetedCvUseCase(
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        orchestrator=FakeOrchestrator(),
    )

    result = use_case.execute(
        filename="resume.txt",
        content_type="text/plain",
        stream=BytesIO(b"hello"),
        job_description="Data platform architect",
        graph_id="cv_rewrite_v1",
    )

    assert result.generation_result.graph_id == "cv_rewrite_v1"


def test_generate_targeted_cv_use_case_cleans_up_file_on_generation_failure() -> None:
    storage = FakeStorage()
    use_case = GenerateTargetedCvUseCase(
        storage=storage,
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        orchestrator=FailingOrchestrator(),
    )

    with pytest.raises(RuntimeError, match="orchestrator failed"):
        use_case.execute(
            filename="resume.txt",
            content_type="text/plain",
            stream=BytesIO(b"hello"),
            job_description="Data platform architect",
        )

    assert storage.deleted_paths == ["/tmp/input.txt"]
