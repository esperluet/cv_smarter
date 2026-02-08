from typing import BinaryIO

from app.application.dto.cv_generation_result import CvGenerationUploadResult
from app.application.errors import InvalidJobDescriptionError, MissingFileNameError, UploadedFileTooLargeError
from app.application.use_cases.process_document_pipeline import ProcessDocumentPipelineUseCase
from app.domain.models.document_pipeline import InputDocument
from app.domain.services.cv_generation_orchestrator import CvGenerationOrchestrator
from app.domain.services.file_storage import FileStorage, FileTooLargeError


class GenerateTargetedCvUseCase:
    def __init__(
        self,
        *,
        storage: FileStorage,
        max_upload_size_bytes: int,
        document_pipeline: ProcessDocumentPipelineUseCase,
        orchestrator: CvGenerationOrchestrator,
        max_job_description_chars: int = 12000,
        preserve_failed_uploads: bool = False,
    ) -> None:
        self._storage = storage
        self._max_upload_size_bytes = max_upload_size_bytes
        self._document_pipeline = document_pipeline
        self._orchestrator = orchestrator
        self._max_job_description_chars = max_job_description_chars
        self._preserve_failed_uploads = preserve_failed_uploads

    def execute(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        stream: BinaryIO,
        job_description: str,
        graph_id: str | None = None,
    ) -> CvGenerationUploadResult:
        if not filename:
            raise MissingFileNameError("Missing file name")

        normalized_job_description = job_description.strip()
        if not normalized_job_description:
            raise InvalidJobDescriptionError("Job description is required")
        if len(normalized_job_description) > self._max_job_description_chars:
            raise InvalidJobDescriptionError(
                f"Job description is too long (max {self._max_job_description_chars} characters)"
            )

        normalized_content_type = content_type or "application/octet-stream"

        try:
            stored_file = self._storage.save_from_stream(
                stream=stream,
                original_name=filename,
                content_type=normalized_content_type,
                max_size_bytes=self._max_upload_size_bytes,
            )
        except FileTooLargeError as exc:
            raise UploadedFileTooLargeError("File is too large") from exc

        try:
            processing_result = self._document_pipeline.execute(
                source_document=InputDocument(
                    source_path=stored_file.storage_path,
                    original_name=stored_file.original_name,
                    media_type=stored_file.content_type,
                ),
                output_formats=(),
            )

            generation_result = self._orchestrator.generate(
                cv_text=processing_result.canonical_document.text,
                job_description=normalized_job_description,
                graph_id=graph_id,
            )
        except Exception:
            self._cleanup_failed_upload(str(stored_file.storage_path))
            raise

        return CvGenerationUploadResult(
            filename=stored_file.original_name,
            content_type=stored_file.content_type,
            size_bytes=stored_file.size_bytes,
            storage_path=str(stored_file.storage_path),
            processing_report=processing_result.report,
            generation_result=generation_result,
        )

    def _cleanup_failed_upload(self, storage_path: str) -> None:
        if self._preserve_failed_uploads:
            return
        try:
            self._storage.delete(storage_path=storage_path)
        except Exception:
            pass
