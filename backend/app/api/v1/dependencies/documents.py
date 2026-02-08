from functools import lru_cache

from app.api.v1.dependencies.document_pipeline import get_document_pipeline_use_case, resolve_output_formats
from app.application.use_cases.process_document_upload import ProcessDocumentUploadUseCase
from app.core.settings import settings
from app.infrastructure.security.artifact_access_token_service import ArtifactAccessTokenService
from app.infrastructure.storage.local_file_storage import LocalFileStorage


@lru_cache(maxsize=1)
def get_document_upload_use_case() -> ProcessDocumentUploadUseCase:
    storage = LocalFileStorage(upload_dir=settings.upload_dir)
    return ProcessDocumentUploadUseCase(
        storage=storage,
        max_upload_size_bytes=settings.max_upload_size_bytes,
        document_pipeline=get_document_pipeline_use_case(),
        output_formats=resolve_output_formats(),
        preserve_failed_uploads=settings.preserve_failed_uploads,
    )


@lru_cache(maxsize=1)
def get_artifact_access_token_service() -> ArtifactAccessTokenService:
    return ArtifactAccessTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        ttl_seconds=settings.artifact_download_token_ttl_seconds,
    )
