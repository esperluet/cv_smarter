from datetime import UTC, datetime

import pytest

pytest.importorskip("langgraph")

from app.domain.services.llm_gateway import LLMRequest
from app.domain.services.prompt_repository import PromptTemplate
from app.domain.services.trace_store import TraceEvent
from app.infrastructure.langgraph.config import (
    CvGenerationRuntimeConfig,
    GraphDefinitionConfig,
    GraphRegistryConfig,
    GraphStageConfig,
    LLMProfileConfig,
    ProviderConfig,
)
from app.infrastructure.langgraph.cv_generation_graph import LangGraphCvGenerationOrchestrator


class FakeGateway:
    def generate(self, request: LLMRequest) -> str:
        if request.stage == "determine_orientation":
            return '{"ats_weight": 0.5, "recruiter_weight": 0.2, "technical_weight": 0.3, "rationale": "Needs ATS-heavy phrasing"}'
        return f"{request.stage} output"


class FakePromptRepo:
    def get(self, prompt_id: str) -> PromptTemplate:
        content_map = {
            "cv_rewrite_v1/determine_orientation": "{cv_text}\n{job_description}",
            "cv_rewrite_v1/ats_pass": "{latest_cv}\n{job_description}\n{orientation_json}",
            "cv_rewrite_v1/recruiter_pass": "{previous_cv}\n{job_description}\n{orientation_json}",
            "cv_rewrite_v1/technical_pass": "{previous_cv}\n{job_description}\n{orientation_json}",
            "cv_rewrite_v1/final_render": "{previous_cv}\n{job_description}\n{orientation_json}",
        }
        return PromptTemplate(
            prompt_id=prompt_id,
            content=content_map[prompt_id],
            version="v1",
            sha256="abc123",
        )


class FakeTraceStore:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def record(self, event: TraceEvent) -> None:
        self.events.append(event)


def _build_runtime_config() -> CvGenerationRuntimeConfig:
    graph = GraphDefinitionConfig(
        graph_id="cv_rewrite_v1",
        version="1",
        orientation_stage_id="determine_orientation",
        final_stage_id="final_render",
        stages=[
            GraphStageConfig(
                stage_id="determine_orientation",
                role="orientation",
                prompt_id="cv_rewrite_v1/determine_orientation",
                llm_profile="default",
                response_format="json",
                update_latest_cv=False,
            ),
            GraphStageConfig(
                stage_id="ats_pass",
                role="rewrite",
                prompt_id="cv_rewrite_v1/ats_pass",
                llm_profile="default",
                response_format="text",
                update_latest_cv=True,
            ),
            GraphStageConfig(
                stage_id="recruiter_pass",
                role="rewrite",
                prompt_id="cv_rewrite_v1/recruiter_pass",
                llm_profile="default",
                response_format="text",
                update_latest_cv=True,
            ),
            GraphStageConfig(
                stage_id="technical_pass",
                role="rewrite",
                prompt_id="cv_rewrite_v1/technical_pass",
                llm_profile="default",
                response_format="text",
                update_latest_cv=True,
            ),
            GraphStageConfig(
                stage_id="final_render",
                role="final",
                prompt_id="cv_rewrite_v1/final_render",
                llm_profile="default",
                response_format="text",
                update_latest_cv=True,
            ),
        ],
    )

    return CvGenerationRuntimeConfig(
        providers={"mock": ProviderConfig(provider_id="mock", kind="mock")},
        llm_profiles={
            "default": LLMProfileConfig(profile_id="default", provider="mock", model="mock-model"),
        },
        graph_registry=GraphRegistryConfig(default_graph_id="cv_rewrite_v1", graphs={"cv_rewrite_v1": graph}),
    )


def test_langgraph_orchestrator_runs_all_stages() -> None:
    trace_store = FakeTraceStore()

    orchestrator = LangGraphCvGenerationOrchestrator(
        config=_build_runtime_config(),
        llm_gateway=FakeGateway(),
        prompt_repository=FakePromptRepo(),
        trace_store=trace_store,
    )

    result = orchestrator.generate(cv_text="My CV", job_description="Data platform architect")

    assert result.graph_id == "cv_rewrite_v1"
    assert result.graph_version == "1"
    assert result.final_cv == "final_render output"
    assert result.orientation.ats_weight > result.orientation.recruiter_weight
    assert len(result.stage_traces) == 5
    completed = [event for event in trace_store.events if event.event == "stage_completed"]
    assert len(completed) == 5


def test_stage_trace_timestamps_are_utc() -> None:
    orchestrator = LangGraphCvGenerationOrchestrator(
        config=_build_runtime_config(),
        llm_gateway=FakeGateway(),
        prompt_repository=FakePromptRepo(),
        trace_store=FakeTraceStore(),
    )
    result = orchestrator.generate(cv_text="x", job_description="y")

    first_trace = result.stage_traces[0]
    assert isinstance(first_trace.started_at, datetime)
    assert first_trace.started_at.tzinfo == UTC
