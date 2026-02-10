from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.v1.dependencies.auth import AuthenticatedUser, get_current_user
from app.api.v1.dependencies.cv import get_cv_upload_use_case
from app.api.v1.dependencies.documents import get_artifact_access_token_service
from app.api.v1.schemas.cv import CVUploadResponse
from app.application.errors import (
    ArtifactPersistenceError,
    IngestionFailedError,
    IngestorNotFoundError,
    LowQualityExtractionError,
    MissingFileNameError,
    RenderingFailedError,
    UploadedFileTooLargeError,
)
from app.application.use_cases.process_cv_upload import ProcessCVUploadUseCase
from app.core.settings import settings
from app.infrastructure.security.artifact_access_token_service import ArtifactAccessTokenService

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/upload", response_model=CVUploadResponse)
def upload_cv(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[ProcessCVUploadUseCase, Depends(get_cv_upload_use_case)],
    artifact_tokens: Annotated[ArtifactAccessTokenService, Depends(get_artifact_access_token_service)],
    file: UploadFile = File(...),
) -> CVUploadResponse:
    try:
        analysis = use_case.execute(filename=file.filename, content_type=file.content_type, stream=file.file)
    except MissingFileNameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UploadedFileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except IngestorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except (IngestionFailedError, LowQualityExtractionError, RenderingFailedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ArtifactPersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return CVUploadResponse(
        filename=analysis.filename,
        content_type=analysis.content_type,
        size_bytes=analysis.size_bytes,
        storage_path=analysis.storage_path,
        metrics=analysis.metrics,
        artifacts=[
            _to_artifact_response(
                storage_path=artifact.storage_path,
                output_format=artifact.format,
                media_type=artifact.media_type,
                user_id=current_user.id,
                token_service=artifact_tokens,
            )
            for artifact in analysis.artifacts
        ],
        processing_report=(
            {
                "engine_name": analysis.processing_report.engine_name,
                "engine_version": analysis.processing_report.engine_version,
                "warnings": analysis.processing_report.warnings,
                "quality_score": analysis.processing_report.quality_score,
                "quality_flags": analysis.processing_report.quality_flags,
                "engine_attempts": analysis.processing_report.engine_attempts,
            }
            if analysis.processing_report is not None
            else None
        ),
    )


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
