from io import BytesIO
from pathlib import Path

import pytest

from app.application.errors import IngestorNotFoundError, MissingFileNameError, UploadedFileTooLargeError
from app.application.use_cases.process_cv_upload import ProcessCVUploadUseCase
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
                "storage_path": Path("/tmp/fake.txt"),
            },
        )

    def delete(self, *, storage_path: str) -> None:
        self.deleted_paths.append(storage_path)


class FakeAnalyzer:
    def analyze(self, file_path: Path) -> dict[str, int]:
        return {"words": 2}


class FailingAnalyzer:
    def analyze(self, file_path: Path) -> dict[str, int]:
        raise RuntimeError("analysis failed")


class RejectingPipeline:
    def execute(self, *, source_document, output_formats):
        raise IngestorNotFoundError("No ingestor registered for media type: application/octet-stream")


def test_upload_use_case_success() -> None:
    use_case = ProcessCVUploadUseCase(storage=FakeStorage(), analyzer=FakeAnalyzer(), max_upload_size_bytes=1024)

    result = use_case.execute(
        filename="resume.txt",
        content_type="text/plain",
        stream=BytesIO(b"hello world"),
    )

    assert result.filename == "resume.txt"
    assert result.size_bytes == 11
    assert result.metrics == {"words": 2}
    assert result.artifacts == []
    assert result.processing_report is None


def test_upload_use_case_missing_filename() -> None:
    use_case = ProcessCVUploadUseCase(storage=FakeStorage(), analyzer=FakeAnalyzer(), max_upload_size_bytes=1024)

    with pytest.raises(MissingFileNameError):
        use_case.execute(filename=None, content_type="text/plain", stream=BytesIO(b"x"))


def test_upload_use_case_surfaces_pipeline_unsupported_content_type() -> None:
    storage = FakeStorage()
    use_case = ProcessCVUploadUseCase(
        storage=storage,
        analyzer=FakeAnalyzer(),
        max_upload_size_bytes=1024,
        document_pipeline=RejectingPipeline(),
    )

    with pytest.raises(IngestorNotFoundError):
        use_case.execute(filename="resume.exe", content_type="application/octet-stream", stream=BytesIO(b"x"))
    assert storage.deleted_paths == ["/tmp/fake.txt"]


def test_upload_use_case_too_large() -> None:
    use_case = ProcessCVUploadUseCase(
        storage=FakeStorage(should_raise_too_large=True),
        analyzer=FakeAnalyzer(),
        max_upload_size_bytes=1024,
    )

    with pytest.raises(UploadedFileTooLargeError):
        use_case.execute(filename="resume.txt", content_type="text/plain", stream=BytesIO(b"x"))


def test_upload_use_case_cleans_up_file_on_analysis_failure() -> None:
    storage = FakeStorage()
    use_case = ProcessCVUploadUseCase(storage=storage, analyzer=FailingAnalyzer(), max_upload_size_bytes=1024)

    with pytest.raises(RuntimeError, match="analysis failed"):
        use_case.execute(filename="resume.txt", content_type="text/plain", stream=BytesIO(b"x"))

    assert storage.deleted_paths == ["/tmp/fake.txt"]
