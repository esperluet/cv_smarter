from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.v1.dependencies.auth import AuthenticatedUser, get_current_user
from app.api.v1.dependencies.documents import get_artifact_access_token_service, get_document_upload_use_case
from app.api.v1.schemas.documents import DocumentProcessResponse
from app.application.errors import (
    ArtifactPersistenceError,
    IngestionFailedError,
    IngestorNotFoundError,
    LowQualityExtractionError,
    MissingFileNameError,
    RenderingFailedError,
    UnsupportedOutputFormatError,
    UploadedFileTooLargeError,
)
from app.application.use_cases.process_document_upload import ProcessDocumentUploadUseCase
from app.core.settings import settings
from app.infrastructure.security.artifact_access_token_service import ArtifactAccessTokenService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/process", response_model=DocumentProcessResponse)
def process_document(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[ProcessDocumentUploadUseCase, Depends(get_document_upload_use_case)],
    artifact_tokens: Annotated[ArtifactAccessTokenService, Depends(get_artifact_access_token_service)],
    file: UploadFile = File(...),
) -> DocumentProcessResponse:
    try:
        result = use_case.execute(filename=file.filename, content_type=file.content_type, stream=file.file)
    except MissingFileNameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UploadedFileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except IngestorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except UnsupportedOutputFormatError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except (IngestionFailedError, LowQualityExtractionError, RenderingFailedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ArtifactPersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    processing = result.processing_result
    return DocumentProcessResponse(
        filename=result.filename,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
        storage_path=result.storage_path,
        canonical_document={
            "schema_version": processing.canonical_document.schema_version,
            "source_media_type": processing.canonical_document.source_media_type,
            "text": processing.canonical_document.text,
            "metadata": processing.canonical_document.metadata,
        },
        processing_report={
            "engine_name": processing.report.engine_name,
            "engine_version": processing.report.engine_version,
            "warnings": processing.report.warnings,
            "quality_score": processing.report.quality_score,
            "quality_flags": processing.report.quality_flags,
            "engine_attempts": processing.report.engine_attempts,
        },
        artifacts=[
            _to_artifact_response(
                storage_path=artifact.storage_path,
                output_format=artifact.format,
                media_type=artifact.media_type,
                user_id=current_user.id,
                token_service=artifact_tokens,
            )
            for artifact in processing.artifacts
        ],
    )


@router.get("/artifacts/download")
def download_artifact(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    token_service: Annotated[ArtifactAccessTokenService, Depends(get_artifact_access_token_service)],
    storage_path: Annotated[str, Query(description="Artifact path returned by /documents/process")],
    token: Annotated[str | None, Query(description="Signed access token from artifact payload")] = None,
) -> FileResponse:
    artifact_path = Path(storage_path).resolve()
    artifact_root = Path(settings.artifact_dir).resolve()

    if settings.use_signed_artifact_download():
        if not token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Artifact token is required")
        try:
            payload = token_service.verify_token(token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid artifact token") from exc
        if payload.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Artifact token user mismatch")
        if payload.storage_path != str(artifact_path):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Artifact token path mismatch")

    if artifact_root not in artifact_path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact path")
    if artifact_path.suffix not in {".md", ".json"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported artifact type")
    if not artifact_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    media_type = "text/markdown" if artifact_path.suffix == ".md" else "application/json"
    return FileResponse(path=artifact_path, media_type=media_type, filename=artifact_path.name)


def _to_artifact_response(
    *,
    storage_path: str,
    output_format: str,
    media_type: str,
    user_id: str,
    token_service: ArtifactAccessTokenService,
) -> dict[str, str | None]:
    payload: dict[str, str | None] = {
        "format": output_format,
        "media_type": media_type,
        "storage_path": storage_path,
    }
    if not settings.use_signed_artifact_download():
        return payload

    resolved_storage_path = str(Path(storage_path).resolve())
    token = token_service.create_token(user_id=user_id, storage_path=resolved_storage_path)
    payload["download_token"] = token
    payload["download_url"] = (
        f"/api/v1/documents/artifacts/download?storage_path={quote(resolved_storage_path)}&token={quote(token)}"
    )
    return payload
