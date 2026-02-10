from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest

from app.application.errors import (
    GroundSourceNotFoundError,
    InvalidGroundSourceNameError,
    InvalidJobDescriptionError,
    MissingFileNameError,
    UploadedFileTooLargeError,
)
from app.application.use_cases.create_ground_source import CreateGroundSourceUseCase
from app.application.use_cases.delete_ground_source import DeleteGroundSourceUseCase
from app.application.use_cases.generate_targeted_cv_from_source import GenerateTargetedCvFromSourceUseCase
from app.application.use_cases.list_ground_sources import ListGroundSourcesUseCase
from app.domain.models.cv_generation import CvGenerationResult, OrientationDecision
from app.domain.models.document_pipeline import CanonicalDocument, DocumentProcessingResult, ProcessingReport
from app.domain.models.ground_source import GroundSource
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
                "storage_path": Path("/tmp/fake_source.txt"),
            },
        )

    def delete(self, *, storage_path: str) -> None:
        self.deleted_paths.append(storage_path)


class FailingCleanupStorage:
    def delete(self, *, storage_path: str) -> None:
        raise RuntimeError("cleanup failed")


class FakePipeline:
    def execute(self, *, source_document, output_formats):
        assert output_formats == ()
        return DocumentProcessingResult(
            canonical_document=CanonicalDocument(
                schema_version="1.0",
                source_media_type=source_document.media_type,
                text="ground source canonical text",
            ),
            report=ProcessingReport(engine_name="fake_ingestor", engine_version="1"),
            artifacts=[],
        )


class FailingPipeline:
    def execute(self, *, source_document, output_formats):
        raise RuntimeError("pipeline failed")


class FakeSourceRepository:
    def __init__(self) -> None:
        self.items: dict[str, GroundSource] = {}
        self._counter = 0

    def create(
        self,
        *,
        user_id: str,
        name: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        storage_path: str,
        canonical_text: str,
        content_hash: str,
    ) -> GroundSource:
        self._counter += 1
        created = GroundSource(
            id=f"source_{self._counter}",
            user_id=user_id,
            name=name,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            canonical_text=canonical_text,
            content_hash=content_hash,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.items[created.id] = created
        return created

    def list_for_user(self, *, user_id: str) -> list[GroundSource]:
        return [item for item in self.items.values() if item.user_id == user_id]

    def get_for_user(self, *, source_id: str, user_id: str) -> GroundSource | None:
        source = self.items.get(source_id)
        if source is None or source.user_id != user_id:
            return None
        return source

    def delete_for_user(self, *, source_id: str, user_id: str) -> bool:
        source = self.items.get(source_id)
        if source is None or source.user_id != user_id:
            return False
        del self.items[source_id]
        return True


class FakeOrchestrator:
    def __init__(self) -> None:
        self.last_call: tuple[str, str, str | None] | None = None

    def generate(self, *, cv_text: str, job_description: str, graph_id: str | None = None) -> CvGenerationResult:
        self.last_call = (cv_text, job_description, graph_id)
        return CvGenerationResult(
            run_id="run_123",
            graph_id=graph_id or "cv_rewrite_v1",
            graph_version="1",
            final_cv="final cv output",
            orientation=OrientationDecision(
                ats_weight=0.34,
                recruiter_weight=0.33,
                technical_weight=0.33,
                rationale="balanced",
            ),
        )


def test_create_ground_source_success() -> None:
    repository = FakeSourceRepository()
    use_case = CreateGroundSourceUseCase(
        sources=repository,
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
    )

    result = use_case.execute(
        user_id="user_1",
        name="Primary resume",
        filename="resume.txt",
        content_type="text/plain",
        stream=BytesIO(b"hello"),
    )

    assert result.source.id == "source_1"
    assert result.source.name == "Primary resume"
    assert result.source.canonical_text == "ground source canonical text"
    assert result.processing_report.engine_name == "fake_ingestor"


def test_create_ground_source_rejects_missing_filename() -> None:
    use_case = CreateGroundSourceUseCase(
        sources=FakeSourceRepository(),
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
    )

    with pytest.raises(MissingFileNameError):
        use_case.execute(
            user_id="user_1",
            name="Primary resume",
            filename=None,
            content_type="text/plain",
            stream=BytesIO(b"x"),
        )


def test_create_ground_source_rejects_empty_name() -> None:
    use_case = CreateGroundSourceUseCase(
        sources=FakeSourceRepository(),
        storage=FakeStorage(),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
    )

    with pytest.raises(InvalidGroundSourceNameError):
        use_case.execute(
            user_id="user_1",
            name="   ",
            filename="resume.txt",
            content_type="text/plain",
            stream=BytesIO(b"x"),
        )


def test_create_ground_source_rejects_too_large_upload() -> None:
    use_case = CreateGroundSourceUseCase(
        sources=FakeSourceRepository(),
        storage=FakeStorage(should_raise_too_large=True),
        max_upload_size_bytes=1024,
        document_pipeline=FakePipeline(),
    )

    with pytest.raises(UploadedFileTooLargeError):
        use_case.execute(
            user_id="user_1",
            name="Primary resume",
            filename="resume.txt",
            content_type="text/plain",
            stream=BytesIO(b"x"),
        )


def test_create_ground_source_cleans_up_file_on_pipeline_failure() -> None:
    storage = FakeStorage()
    use_case = CreateGroundSourceUseCase(
        sources=FakeSourceRepository(),
        storage=storage,
        max_upload_size_bytes=1024,
        document_pipeline=FailingPipeline(),
    )

    with pytest.raises(RuntimeError, match="pipeline failed"):
        use_case.execute(
            user_id="user_1",
            name="Primary resume",
            filename="resume.txt",
            content_type="text/plain",
            stream=BytesIO(b"x"),
        )

    assert storage.deleted_paths == ["/tmp/fake_source.txt"]


def test_list_ground_sources_for_user() -> None:
    repository = FakeSourceRepository()
    repository.create(
        user_id="user_1",
        name="Source A",
        original_filename="a.txt",
        content_type="text/plain",
        size_bytes=1,
        storage_path="/tmp/a.txt",
        canonical_text="A",
        content_hash="h1",
    )
    repository.create(
        user_id="user_2",
        name="Source B",
        original_filename="b.txt",
        content_type="text/plain",
        size_bytes=1,
        storage_path="/tmp/b.txt",
        canonical_text="B",
        content_hash="h2",
    )

    use_case = ListGroundSourcesUseCase(sources=repository)
    result = use_case.execute(user_id="user_1")

    assert len(result) == 1
    assert result[0].name == "Source A"


def test_delete_ground_source_not_found() -> None:
    use_case = DeleteGroundSourceUseCase(sources=FakeSourceRepository(), storage=FakeStorage())

    with pytest.raises(GroundSourceNotFoundError):
        use_case.execute(user_id="user_1", source_id="missing")


def test_delete_ground_source_success_deletes_uploaded_file() -> None:
    repository = FakeSourceRepository()
    source = repository.create(
        user_id="user_1",
        name="Source A",
        original_filename="a.txt",
        content_type="text/plain",
        size_bytes=1,
        storage_path="/tmp/a.txt",
        canonical_text="A",
        content_hash="h1",
    )
    storage = FakeStorage()
    use_case = DeleteGroundSourceUseCase(sources=repository, storage=storage)

    use_case.execute(user_id="user_1", source_id=source.id)

    assert repository.get_for_user(source_id=source.id, user_id="user_1") is None
    assert storage.deleted_paths == ["/tmp/a.txt"]


def test_delete_ground_source_keeps_success_when_file_cleanup_fails() -> None:
    repository = FakeSourceRepository()
    source = repository.create(
        user_id="user_1",
        name="Source A",
        original_filename="a.txt",
        content_type="text/plain",
        size_bytes=1,
        storage_path="/tmp/a.txt",
        canonical_text="A",
        content_hash="h1",
    )
    use_case = DeleteGroundSourceUseCase(sources=repository, storage=FailingCleanupStorage())

    use_case.execute(user_id="user_1", source_id=source.id)
    assert repository.get_for_user(source_id=source.id, user_id="user_1") is None


def test_generate_targeted_cv_from_source_success() -> None:
    repository = FakeSourceRepository()
    source = repository.create(
        user_id="user_1",
        name="Primary resume",
        original_filename="resume.txt",
        content_type="text/plain",
        size_bytes=10,
        storage_path="/tmp/resume.txt",
        canonical_text="ground source canonical text",
        content_hash="hash",
    )
    orchestrator = FakeOrchestrator()

    use_case = GenerateTargetedCvFromSourceUseCase(
        sources=repository,
        orchestrator=orchestrator,
    )
    result = use_case.execute(
        user_id="user_1",
        source_id=source.id,
        job_description="Target backend role",
        graph_id="cv_rewrite_v1",
    )

    assert result.source.id == source.id
    assert result.generation_result.run_id == "run_123"
    assert orchestrator.last_call == ("ground source canonical text", "Target backend role", "cv_rewrite_v1")


def test_generate_targeted_cv_from_source_rejects_missing_source() -> None:
    use_case = GenerateTargetedCvFromSourceUseCase(
        sources=FakeSourceRepository(),
        orchestrator=FakeOrchestrator(),
    )

    with pytest.raises(GroundSourceNotFoundError):
        use_case.execute(
            user_id="user_1",
            source_id="missing",
            job_description="Target backend role",
        )


def test_generate_targeted_cv_from_source_rejects_invalid_job_description() -> None:
    repository = FakeSourceRepository()
    source = repository.create(
        user_id="user_1",
        name="Primary resume",
        original_filename="resume.txt",
        content_type="text/plain",
        size_bytes=10,
        storage_path="/tmp/resume.txt",
        canonical_text="ground source canonical text",
        content_hash="hash",
    )
    use_case = GenerateTargetedCvFromSourceUseCase(
        sources=repository,
        orchestrator=FakeOrchestrator(),
    )

    with pytest.raises(InvalidJobDescriptionError):
        use_case.execute(
            user_id="user_1",
            source_id=source.id,
            job_description="   ",
        )
