from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class OrientationDecision:
    ats_weight: float
    recruiter_weight: float
    technical_weight: float
    rationale: str


@dataclass(frozen=True)
class StageExecutionTrace:
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


@dataclass(frozen=True)
class CvGenerationResult:
    run_id: str
    graph_id: str
    graph_version: str
    final_cv: str
    orientation: OrientationDecision
    stage_traces: list[StageExecutionTrace] = field(default_factory=list)
