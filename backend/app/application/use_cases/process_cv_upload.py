from typing import BinaryIO

from app.application.errors import MissingFileNameError, UnsupportedFileTypeError, UploadedFileTooLargeError
from app.application.use_cases.process_document_pipeline import ProcessDocumentPipelineUseCase
from app.domain.models.cv_analysis import CVAnalysis
from app.domain.models.document_pipeline import InputDocument
from app.domain.services.cv_analyzer import CVAnalyzer
from app.domain.services.file_storage import FileStorage, FileTooLargeError


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/tiff",
}


class ProcessCVUploadUseCase:
    def __init__(
        self,
        storage: FileStorage,
        analyzer: CVAnalyzer,
        max_upload_size_bytes: int,
        document_pipeline: ProcessDocumentPipelineUseCase | None = None,
        output_formats: tuple[str, ...] = ("markdown", "json"),
        preserve_failed_uploads: bool = False,
    ) -> None:
        self._storage = storage
        self._analyzer = analyzer
        self._max_upload_size_bytes = max_upload_size_bytes
        self._document_pipeline = document_pipeline
        self._output_formats = output_formats
        self._preserve_failed_uploads = preserve_failed_uploads

    def execute(self, *, filename: str | None, content_type: str | None, stream: BinaryIO) -> CVAnalysis:
        if not filename:
            raise MissingFileNameError("Missing file name")

        normalized_content_type = content_type or "application/octet-stream"
        if normalized_content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedFileTypeError("Unsupported file type")

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
            metrics = self._analyzer.analyze(stored_file.storage_path)
            artifacts = []
            processing_report = None

            if self._document_pipeline is not None:
                pipeline_result = self._document_pipeline.execute(
                    source_document=InputDocument(
                        source_path=stored_file.storage_path,
                        original_name=stored_file.original_name,
                        media_type=stored_file.content_type,
                    ),
                    output_formats=self._output_formats,
                )
                artifacts = pipeline_result.artifacts
                processing_report = pipeline_result.report
        except Exception:
            self._cleanup_failed_upload(str(stored_file.storage_path))
            raise

        return CVAnalysis(
            filename=stored_file.original_name,
            content_type=stored_file.content_type,
            size_bytes=stored_file.size_bytes,
            storage_path=str(stored_file.storage_path),
            metrics=metrics,
            artifacts=artifacts,
            processing_report=processing_report,
        )

    def _cleanup_failed_upload(self, storage_path: str) -> None:
        if self._preserve_failed_uploads:
            return
        try:
            self._storage.delete(storage_path=storage_path)
        except Exception:
            pass
