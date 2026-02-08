from datetime import datetime

from pydantic import BaseModel, Field

from app.api.v1.schemas.cv import ProcessingReportResponse


class GroundSourceResponse(BaseModel):
    id: str
    name: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class GroundSourceCreateResponse(GroundSourceResponse):
    storage_path: str
    processing_report: ProcessingReportResponse


class GroundSourceListResponse(BaseModel):
    items: list[GroundSourceResponse] = Field(default_factory=list)
