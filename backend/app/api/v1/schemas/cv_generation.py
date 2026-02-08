from datetime import datetime

from pydantic import BaseModel, Field

from app.api.v1.schemas.cv import ProcessingReportResponse


class OrientationDecisionResponse(BaseModel):
    ats_weight: float
    recruiter_weight: float
    technical_weight: float
    rationale: str


class StageExecutionTraceResponse(BaseModel):
    stage: str
    prompt_id: str
    prompt_hash: str
    llm_profile: str
    llm_provider: str
    llm_model: str
    status: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    error_message: str | None = None


class CVGenerateResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    run_id: str
    graph_id: str
    graph_version: str
    final_cv: str
    orientation: OrientationDecisionResponse
    stage_traces: list[StageExecutionTraceResponse] = Field(default_factory=list)
    processing_report: ProcessingReportResponse


class CVGenerateFromSourceResponse(BaseModel):
    source_id: str
    source_name: str
    run_id: str
    graph_id: str
    graph_version: str
    final_cv: str
    orientation: OrientationDecisionResponse
    stage_traces: list[StageExecutionTraceResponse] = Field(default_factory=list)


class CVExportPdfRequest(BaseModel):
    content: str
    format_hint: str | None = None
    filename: str | None = None
