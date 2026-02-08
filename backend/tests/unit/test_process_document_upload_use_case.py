from io import BytesIO
from pathlib import Path

import pytest

from app.application.errors import MissingFileNameError, UploadedFileTooLargeError
from app.application.use_cases.process_document_upload import ProcessDocumentUploadUseCase
from app.domain.models.document_pipeline import (
    CanonicalDocument,
    DocumentProcessingResult,
    ProcessingReport,
    RenderedArtifact,
)
from app.domain.services.file_storage import FileTooLargeError


class FakeStorage:
    def __init__(self, should_raise_too_large: bool = False) -> None:
        self.should_raise_too_large = should_raise_too_large
        self.deleted_paths: list[str] = []

    def save_from_stream(self, *, stream, original_name: str, content_type: str, max_size_bytes: int):
        if self.should_raise_too_large:
            raise FileTooLargeError("File is too large")

        payload = stream.read()
        return type(
            "StoredFile",
            (),
            {
                "original_name": original_name,
                "content_type": content_type,
                "size_bytes": len(payload),
                "storage_path": Path("/tmp/fake.pdf"),
            },
        )

    def delete(self, *, storage_path: str) -> None:
        self.deleted_paths.append(storage_path)


class FakePipeline:
    def execute(self, *, source_document, output_formats):
        return DocumentProcessingResult(
            canonical_document=CanonicalDocument(
                schema_version="1.0",
                source_media_type=source_document.media_type,
                text="hello",
            ),
            report=ProcessingReport(engine_name="fake", engine_version="1"),
            artifacts=[
                RenderedArtifact(format="json", media_type="application/json", storage_path="/tmp/fake.json")
            ],
        )


class FailingPipeline:
    def execute(self, *, source_document, output_formats):
        raise RuntimeError("pipeline failed")


def test_document_upload_success() -> None:
    use_case = ProcessDocumentUploadUseCase(
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
        output_formats=("json",),
    )

    result = use_case.execute(
        filename="resume.pdf",
        content_type="application/pdf",
        stream=BytesIO(b"%PDF-1.5"),
    )

    assert result.filename == "resume.pdf"
    assert result.size_bytes == 8
    assert result.processing_result.report.engine_name == "fake"


def test_document_upload_missing_filename() -> None:
    use_case = ProcessDocumentUploadUseCase(
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
    )

    with pytest.raises(MissingFileNameError):
        use_case.execute(filename=None, content_type="application/pdf", stream=BytesIO(b"x"))


def test_document_upload_too_large() -> None:
    use_case = ProcessDocumentUploadUseCase(
        storage=FakeStorage(should_raise_too_large=True),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
    )

    with pytest.raises(UploadedFileTooLargeError):
        use_case.execute(filename="resume.pdf", content_type="application/pdf", stream=BytesIO(b"x"))


def test_document_upload_cleans_up_file_on_pipeline_failure() -> None:
    storage = FakeStorage()
    use_case = ProcessDocumentUploadUseCase(
        storage=storage,
        max_upload_size_bytes=1024,
        document_pipeline=FailingPipeline(),
    )

    with pytest.raises(RuntimeError, match="pipeline failed"):
        use_case.execute(filename="resume.pdf", content_type="application/pdf", stream=BytesIO(b"x"))

    assert storage.deleted_paths == ["/tmp/fake.pdf"]
