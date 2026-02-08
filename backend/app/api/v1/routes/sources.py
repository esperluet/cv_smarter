from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.api.v1.dependencies.auth import AuthenticatedUser, get_current_user
from app.api.v1.dependencies.sources import (
    get_create_ground_source_use_case,
    get_delete_ground_source_use_case,
    get_list_ground_sources_use_case,
)
from app.api.v1.schemas.sources import GroundSourceCreateResponse, GroundSourceListResponse
from app.application.errors import (
    GroundSourceNotFoundError,
    IngestionFailedError,
    IngestorNotFoundError,
    InvalidGroundSourceNameError,
    LowQualityExtractionError,
    MissingFileNameError,
    RenderingFailedError,
    UploadedFileTooLargeError,
)
from app.application.use_cases.create_ground_source import CreateGroundSourceUseCase
from app.application.use_cases.delete_ground_source import DeleteGroundSourceUseCase
from app.application.use_cases.list_ground_sources import ListGroundSourcesUseCase

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=GroundSourceCreateResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[CreateGroundSourceUseCase, Depends(get_create_ground_source_use_case)],
    name: Annotated[str, Form(...)],
    file: UploadFile = File(...),
) -> GroundSourceCreateResponse:
    try:
        result = use_case.execute(
            user_id=current_user.id,
            name=name,
            filename=file.filename,
            content_type=file.content_type,
            stream=file.file,
        )
    except (MissingFileNameError, InvalidGroundSourceNameError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UploadedFileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except IngestorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except (IngestionFailedError, LowQualityExtractionError, RenderingFailedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    source = result.source
    report = result.processing_report
    return GroundSourceCreateResponse(
        id=source.id,
        name=source.name,
        original_filename=source.original_filename,
        content_type=source.content_type,
        size_bytes=source.size_bytes,
        storage_path=source.storage_path,
        created_at=source.created_at,
        updated_at=source.updated_at,
        processing_report={
            "engine_name": report.engine_name,
            "engine_version": report.engine_version,
            "warnings": report.warnings,
            "quality_score": report.quality_score,
            "quality_flags": report.quality_flags,
            "engine_attempts": report.engine_attempts,
        },
    )


@router.get("", response_model=GroundSourceListResponse)
def list_sources(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[ListGroundSourcesUseCase, Depends(get_list_ground_sources_use_case)],
) -> GroundSourceListResponse:
    sources = use_case.execute(user_id=current_user.id)
    return GroundSourceListResponse(
        items=[
            {
                "id": source.id,
                "name": source.name,
                "original_filename": source.original_filename,
                "content_type": source.content_type,
                "size_bytes": source.size_bytes,
                "created_at": source.created_at,
                "updated_at": source.updated_at,
            }
            for source in sources
        ]
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[DeleteGroundSourceUseCase, Depends(get_delete_ground_source_use_case)],
) -> Response:
    try:
        use_case.execute(user_id=current_user.id, source_id=source_id)
    except GroundSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
