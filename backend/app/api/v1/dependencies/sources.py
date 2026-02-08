from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_db
from app.api.v1.dependencies.cv_export import get_export_cv_pdf_use_case
from app.api.v1.dependencies.cv_generation import get_cv_generation_orchestrator
from app.api.v1.dependencies.document_pipeline import get_document_pipeline_use_case
from app.application.use_cases.create_ground_source import CreateGroundSourceUseCase
from app.application.use_cases.delete_ground_source import DeleteGroundSourceUseCase
from app.application.use_cases.export_cv_pdf import ExportCvPdfUseCase
from app.application.use_cases.generate_targeted_cv_from_source import GenerateTargetedCvFromSourceUseCase
from app.application.use_cases.generate_targeted_cv_pdf_from_source import GenerateTargetedCvPdfFromSourceUseCase
from app.application.use_cases.list_ground_sources import ListGroundSourcesUseCase
from app.application.use_cases.process_document_pipeline import ProcessDocumentPipelineUseCase
from app.core.settings import settings
from app.domain.services.cv_generation_orchestrator import CvGenerationOrchestrator
from app.infrastructure.repositories.sqlalchemy_ground_source_repository import SQLAlchemyGroundSourceRepository
from app.infrastructure.storage.local_file_storage import LocalFileStorage


def get_ground_source_repository(
    db: Annotated[Session, Depends(get_db)],
) -> SQLAlchemyGroundSourceRepository:
    return SQLAlchemyGroundSourceRepository(db)


def get_create_ground_source_use_case(
    sources: Annotated[SQLAlchemyGroundSourceRepository, Depends(get_ground_source_repository)],
    document_pipeline: Annotated[ProcessDocumentPipelineUseCase, Depends(get_document_pipeline_use_case)],
) -> CreateGroundSourceUseCase:
    return CreateGroundSourceUseCase(
        sources=sources,
        storage=LocalFileStorage(upload_dir=settings.upload_dir),
        max_upload_size_bytes=settings.max_upload_size_bytes,
        document_pipeline=document_pipeline,
        preserve_failed_uploads=settings.preserve_failed_uploads,
    )


def get_list_ground_sources_use_case(
    sources: Annotated[SQLAlchemyGroundSourceRepository, Depends(get_ground_source_repository)],
) -> ListGroundSourcesUseCase:
    return ListGroundSourcesUseCase(sources=sources)


def get_delete_ground_source_use_case(
    sources: Annotated[SQLAlchemyGroundSourceRepository, Depends(get_ground_source_repository)],
) -> DeleteGroundSourceUseCase:
    return DeleteGroundSourceUseCase(sources=sources)


def get_generate_from_source_use_case(
    sources: Annotated[SQLAlchemyGroundSourceRepository, Depends(get_ground_source_repository)],
    orchestrator: Annotated[CvGenerationOrchestrator, Depends(get_cv_generation_orchestrator)],
) -> GenerateTargetedCvFromSourceUseCase:
    return GenerateTargetedCvFromSourceUseCase(
        sources=sources,
        orchestrator=orchestrator,
        max_job_description_chars=settings.cv_generation_max_job_description_chars,
    )


def get_generate_from_source_pdf_use_case(
    generator: Annotated[GenerateTargetedCvFromSourceUseCase, Depends(get_generate_from_source_use_case)],
    exporter: Annotated[ExportCvPdfUseCase, Depends(get_export_cv_pdf_use_case)],
) -> GenerateTargetedCvPdfFromSourceUseCase:
    return GenerateTargetedCvPdfFromSourceUseCase(
        generator=generator,
        exporter=exporter,
    )
