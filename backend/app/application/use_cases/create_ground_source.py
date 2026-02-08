from hashlib import sha256
from typing import BinaryIO

from app.application.dto.ground_source_result import GroundSourceCreateResult
from app.application.errors import InvalidGroundSourceNameError, MissingFileNameError, UploadedFileTooLargeError
from app.application.use_cases.process_document_pipeline import ProcessDocumentPipelineUseCase
from app.domain.models.document_pipeline import InputDocument
from app.domain.repositories.ground_source_repository import GroundSourceRepository
from app.domain.services.file_storage import FileStorage, FileTooLargeError


class CreateGroundSourceUseCase:
    def __init__(
        self,
        *,
        sources: GroundSourceRepository,
        storage: FileStorage,
        max_upload_size_bytes: int,
        document_pipeline: ProcessDocumentPipelineUseCase,
        max_name_length: int = 120,
        preserve_failed_uploads: bool = False,
    ) -> None:
        self._sources = sources
        self._storage = storage
        self._max_upload_size_bytes = max_upload_size_bytes
        self._document_pipeline = document_pipeline
        self._max_name_length = max_name_length
        self._preserve_failed_uploads = preserve_failed_uploads

    def execute(
        self,
        *,
        user_id: str,
        name: str,
        filename: str | None,
        content_type: str | None,
        stream: BinaryIO,
    ) -> GroundSourceCreateResult:
        if not filename:
            raise MissingFileNameError("Missing file name")

        normalized_name = name.strip()
        if not normalized_name:
            raise InvalidGroundSourceNameError("Ground source name is required")
        if len(normalized_name) > self._max_name_length:
            raise InvalidGroundSourceNameError(
                f"Ground source name is too long (max {self._max_name_length} characters)"
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

            canonical_text = processing_result.canonical_document.text
            content_hash = sha256(canonical_text.encode("utf-8")).hexdigest()

            source = self._sources.create(
                user_id=user_id,
                name=normalized_name,
                original_filename=stored_file.original_name,
                content_type=stored_file.content_type,
                size_bytes=stored_file.size_bytes,
                storage_path=str(stored_file.storage_path),
                canonical_text=canonical_text,
                content_hash=content_hash,
            )
        except Exception:
            self._cleanup_failed_upload(str(stored_file.storage_path))
            raise

        return GroundSourceCreateResult(source=source, processing_report=processing_result.report)

    def _cleanup_failed_upload(self, storage_path: str) -> None:
        if self._preserve_failed_uploads:
            return
        try:
            self._storage.delete(storage_path=storage_path)
        except Exception:
            pass
