from functools import lru_cache

from app.application.use_cases.process_cv_upload import ProcessCVUploadUseCase
from app.api.v1.dependencies.document_pipeline import get_document_pipeline_use_case, resolve_output_formats
from app.core.settings import settings
from app.infrastructure.analysis.basic_cv_analyzer import BasicCVAnalyzer
from app.infrastructure.storage.local_file_storage import LocalFileStorage


@lru_cache(maxsize=1)
def get_cv_upload_use_case() -> ProcessCVUploadUseCase:
    storage = LocalFileStorage(upload_dir=settings.upload_dir)
    analyzer = BasicCVAnalyzer()
    document_pipeline = get_document_pipeline_use_case()
    output_formats = resolve_output_formats()
    return ProcessCVUploadUseCase(
        storage=storage,
        analyzer=analyzer,
        max_upload_size_bytes=settings.max_upload_size_bytes,
        document_pipeline=document_pipeline,
        output_formats=output_formats,
        preserve_failed_uploads=settings.preserve_failed_uploads,
    )
