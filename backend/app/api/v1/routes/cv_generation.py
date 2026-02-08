from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.api.v1.dependencies.auth import AuthenticatedUser, get_current_user
from app.api.v1.dependencies.cv_export import get_export_cv_pdf_use_case
from app.api.v1.dependencies.cv_generation import get_cv_generation_use_case
from app.api.v1.dependencies.sources import get_generate_from_source_pdf_use_case, get_generate_from_source_use_case
from app.api.v1.schemas.cv_generation import CVExportPdfRequest, CVGenerateFromSourceResponse, CVGenerateResponse
from app.application.errors import (
    ArtifactPersistenceError,
    CvExportError,
    CvGenerationConfigurationError,
    CvGenerationExecutionError,
    GroundSourceNotFoundError,
    IngestionFailedError,
    IngestorNotFoundError,
    InvalidJobDescriptionError,
    LowQualityExtractionError,
    MissingFileNameError,
    PromptResolutionError,
    RenderingFailedError,
    UploadedFileTooLargeError,
)
from app.application.use_cases.export_cv_pdf import ExportCvPdfUseCase
from app.application.use_cases.generate_targeted_cv import GenerateTargetedCvUseCase
from app.application.use_cases.generate_targeted_cv_from_source import GenerateTargetedCvFromSourceUseCase
from app.application.use_cases.generate_targeted_cv_pdf_from_source import GenerateTargetedCvPdfFromSourceUseCase

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/generate", response_model=CVGenerateResponse)
def generate_cv(
    _current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[GenerateTargetedCvUseCase, Depends(get_cv_generation_use_case)],
    job_description: Annotated[str, Form(...)],
    graph_id: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
) -> CVGenerateResponse:
    try:
        result = use_case.execute(
            filename=file.filename,
            content_type=file.content_type,
            stream=file.file,
            job_description=job_description,
            graph_id=graph_id,
        )
    except (MissingFileNameError, InvalidJobDescriptionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UploadedFileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except IngestorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except (IngestionFailedError, LowQualityExtractionError, RenderingFailedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except (CvGenerationConfigurationError, PromptResolutionError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except CvGenerationExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ArtifactPersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    generation = result.generation_result
    orientation = generation.orientation

    return CVGenerateResponse(
        filename=result.filename,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
        storage_path=result.storage_path,
        run_id=generation.run_id,
        graph_id=generation.graph_id,
        graph_version=generation.graph_version,
        final_cv=generation.final_cv,
        orientation={
            "ats_weight": orientation.ats_weight,
            "recruiter_weight": orientation.recruiter_weight,
            "technical_weight": orientation.technical_weight,
            "rationale": orientation.rationale,
        },
        stage_traces=[
            {
                "stage": trace.stage,
                "prompt_id": trace.prompt_id,
                "prompt_hash": trace.prompt_hash,
                "llm_profile": trace.llm_profile,
                "llm_provider": trace.llm_provider,
                "llm_model": trace.llm_model,
                "status": trace.status,
                "started_at": trace.started_at,
                "ended_at": trace.ended_at,
                "duration_ms": trace.duration_ms,
                "error_message": trace.error_message,
            }
            for trace in generation.stage_traces
        ],
        processing_report={
            "engine_name": result.processing_report.engine_name,
            "engine_version": result.processing_report.engine_version,
            "warnings": result.processing_report.warnings,
            "quality_score": result.processing_report.quality_score,
            "quality_flags": result.processing_report.quality_flags,
            "engine_attempts": result.processing_report.engine_attempts,
        },
    )


@router.post("/export/pdf")
def export_cv_pdf(
    _current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    payload: CVExportPdfRequest,
    use_case: Annotated[ExportCvPdfUseCase, Depends(get_export_cv_pdf_use_case)],
) -> Response:
    try:
        result = use_case.execute(
            content=payload.content,
            format_hint=payload.format_hint,
            filename=payload.filename or "cv_export.pdf",
        )
    except CvExportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
    }
    return Response(content=result.content_bytes, media_type=result.media_type, headers=headers)


@router.post("/generate-from-source", response_model=CVGenerateFromSourceResponse)
def generate_cv_from_source(
    _current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[GenerateTargetedCvFromSourceUseCase, Depends(get_generate_from_source_use_case)],
    source_id: Annotated[str, Form(...)],
    job_description: Annotated[str, Form(...)],
    graph_id: Annotated[str | None, Form()] = None,
) -> CVGenerateFromSourceResponse:
    try:
        result = use_case.execute(
            user_id=_current_user.id,
            source_id=source_id,
            job_description=job_description,
            graph_id=graph_id,
        )
    except GroundSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidJobDescriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (CvGenerationConfigurationError, PromptResolutionError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except CvGenerationExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    generation = result.generation_result
    orientation = generation.orientation

    return CVGenerateFromSourceResponse(
        source_id=result.source.id,
        source_name=result.source.name,
        run_id=generation.run_id,
        graph_id=generation.graph_id,
        graph_version=generation.graph_version,
        final_cv=generation.final_cv,
        orientation={
            "ats_weight": orientation.ats_weight,
            "recruiter_weight": orientation.recruiter_weight,
            "technical_weight": orientation.technical_weight,
            "rationale": orientation.rationale,
        },
        stage_traces=[
            {
                "stage": trace.stage,
                "prompt_id": trace.prompt_id,
                "prompt_hash": trace.prompt_hash,
                "llm_profile": trace.llm_profile,
                "llm_provider": trace.llm_provider,
                "llm_model": trace.llm_model,
                "status": trace.status,
                "started_at": trace.started_at,
                "ended_at": trace.ended_at,
                "duration_ms": trace.duration_ms,
                "error_message": trace.error_message,
            }
            for trace in generation.stage_traces
        ],
    )


@router.post("/generate-from-source/pdf")
def generate_cv_from_source_pdf(
    _current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[GenerateTargetedCvPdfFromSourceUseCase, Depends(get_generate_from_source_pdf_use_case)],
    source_id: Annotated[str, Form(...)],
    job_description: Annotated[str, Form(...)],
    graph_id: Annotated[str | None, Form()] = None,
    format_hint: Annotated[str | None, Form()] = None,
) -> Response:
    try:
        result = use_case.execute(
            user_id=_current_user.id,
            source_id=source_id,
            job_description=job_description,
            graph_id=graph_id,
            format_hint=format_hint,
        )
    except GroundSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidJobDescriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (CvGenerationConfigurationError, PromptResolutionError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except CvGenerationExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except CvExportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
    }
    if result.run_id:
        headers["X-CV-Run-Id"] = result.run_id

    return Response(content=result.content_bytes, media_type=result.media_type, headers=headers)
