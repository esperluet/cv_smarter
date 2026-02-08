import json
import re
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import uuid4

from app.application.errors import CvGenerationExecutionError, PromptResolutionError
from app.domain.models.cv_generation import CvGenerationResult, OrientationDecision, StageExecutionTrace
from app.domain.services.cv_generation_orchestrator import CvGenerationOrchestrator
from app.domain.services.llm_gateway import LLMGateway, LLMRequest
from app.domain.services.prompt_repository import PromptRepository
from app.domain.services.trace_store import TraceEvent, TraceStore
from app.infrastructure.langgraph.config import CvGenerationRuntimeConfig, GraphDefinitionConfig, GraphStageConfig

try:
    from langgraph.graph import END, START, StateGraph
except ImportError as exc:  # pragma: no cover - explicit runtime failure path
    raise ImportError(
        "langgraph is required for CV generation orchestration. "
        "Install project dependencies to enable this feature."
    ) from exc


class CvGenerationState(TypedDict):
    run_id: str
    graph_id: str
    graph_version: str
    cv_text: str
    job_description: str
    latest_cv: str
    orientation: OrientationDecision
    orientation_json: str
    stage_outputs: dict[str, str]
    stage_traces: list[StageExecutionTrace]


class LangGraphCvGenerationOrchestrator(CvGenerationOrchestrator):
    def __init__(
        self,
        *,
        config: CvGenerationRuntimeConfig,
        llm_gateway: LLMGateway,
        prompt_repository: PromptRepository,
        trace_store: TraceStore,
    ) -> None:
        self._config = config
        self._llm_gateway = llm_gateway
        self._prompt_repository = prompt_repository
        self._trace_store = trace_store
        self._compiled_graphs: dict[str, Any] = {}

    def generate(
        self,
        *,
        cv_text: str,
        job_description: str,
        graph_id: str | None = None,
    ) -> CvGenerationResult:
        definition = self._config.resolve_graph(graph_id)
        run_id = str(uuid4())
        initial_state: CvGenerationState = {
            "run_id": run_id,
            "graph_id": definition.graph_id,
            "graph_version": definition.version,
            "cv_text": cv_text,
            "job_description": job_description,
            "latest_cv": cv_text,
            "orientation": OrientationDecision(
                ats_weight=0.34,
                recruiter_weight=0.33,
                technical_weight=0.33,
                rationale="Default orientation before model decision.",
            ),
            "orientation_json": "",
            "stage_outputs": {},
            "stage_traces": [],
        }

        graph = self._get_or_compile_graph(definition)
        final_state = graph.invoke(initial_state)

        final_stage_id = definition.final_stage_id or definition.stages[-1].stage_id
        final_cv = final_state["stage_outputs"].get(final_stage_id, final_state["latest_cv"])

        return CvGenerationResult(
            run_id=run_id,
            graph_id=definition.graph_id,
            graph_version=definition.version,
            final_cv=final_cv,
            orientation=final_state["orientation"],
            stage_traces=final_state["stage_traces"],
        )

    def _get_or_compile_graph(self, definition: GraphDefinitionConfig):
        cache_key = f"{definition.graph_id}:{definition.version}"
        if cache_key in self._compiled_graphs:
            return self._compiled_graphs[cache_key]

        graph_builder = StateGraph(CvGenerationState)

        for stage in definition.stages:
            graph_builder.add_node(stage.stage_id, self._build_stage_node(definition, stage))

        first_stage_id = definition.stages[0].stage_id
        graph_builder.add_edge(START, first_stage_id)

        for previous, current in zip(definition.stages, definition.stages[1:], strict=False):
            graph_builder.add_edge(previous.stage_id, current.stage_id)

        graph_builder.add_edge(definition.stages[-1].stage_id, END)
        compiled = graph_builder.compile()
        self._compiled_graphs[cache_key] = compiled
        return compiled

    def _build_stage_node(self, definition: GraphDefinitionConfig, stage: GraphStageConfig):
        def _node(state: CvGenerationState) -> dict[str, object]:
            variables = self._build_prompt_variables(state)
            output, trace = self._run_stage(
                definition=definition,
                stage=stage,
                state=state,
                variables=variables,
            )

            stage_outputs = {**state["stage_outputs"], stage.stage_id: output}
            updates: dict[str, object] = {
                "stage_outputs": stage_outputs,
                "stage_traces": [*state["stage_traces"], trace],
            }

            if stage.role == "orientation":
                orientation = _parse_orientation(output)
                updates["orientation"] = orientation
                updates["orientation_json"] = json.dumps(
                    {
                        "ats_weight": orientation.ats_weight,
                        "recruiter_weight": orientation.recruiter_weight,
                        "technical_weight": orientation.technical_weight,
                        "rationale": orientation.rationale,
                    }
                )

            if stage.update_latest_cv:
                updates["latest_cv"] = output

            return updates

        return _node

    def _run_stage(
        self,
        *,
        definition: GraphDefinitionConfig,
        stage: GraphStageConfig,
        state: CvGenerationState,
        variables: dict[str, str],
    ) -> tuple[str, StageExecutionTrace]:
        profile = self._config.get_profile(stage.llm_profile)
        provider = self._config.get_provider(profile.provider)
        prompt = self._prompt_repository.get(stage.prompt_id)
        rendered_prompt = self._render_prompt(prompt.content, variables)

        started_at = _utc_now()
        self._trace_store.record(
            TraceEvent(
                run_id=state["run_id"],
                stage=stage.stage_id,
                event="stage_started",
                timestamp=started_at,
                payload={
                    "graph_id": definition.graph_id,
                    "graph_version": definition.version,
                    "stage_role": stage.role,
                    "prompt_id": prompt.prompt_id,
                    "prompt_version": prompt.version,
                    "prompt_hash": prompt.sha256,
                    "llm_profile": profile.profile_id,
                    "llm_provider": profile.provider,
                    "llm_model": profile.model,
                },
            )
        )

        try:
            output = self._llm_gateway.generate(
                LLMRequest(
                    stage=stage.stage_id,
                    provider=profile.provider,
                    model=profile.model,
                    prompt=rendered_prompt,
                    temperature=profile.temperature,
                    max_tokens=profile.max_tokens,
                    timeout_seconds=provider.timeout_seconds,
                )
            )
        except Exception as exc:
            ended_at = _utc_now()
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
            self._trace_store.record(
                TraceEvent(
                    run_id=state["run_id"],
                    stage=stage.stage_id,
                    event="stage_failed",
                    timestamp=ended_at,
                    payload={
                        "graph_id": definition.graph_id,
                        "graph_version": definition.version,
                        "error": str(exc),
                        "duration_ms": duration_ms,
                    },
                )
            )
            raise CvGenerationExecutionError(
                f"CV generation failed at graph '{definition.graph_id}' stage '{stage.stage_id}'"
            ) from exc

        ended_at = _utc_now()
        duration_ms = int((ended_at - started_at).total_seconds() * 1000)

        self._trace_store.record(
            TraceEvent(
                run_id=state["run_id"],
                stage=stage.stage_id,
                event="stage_completed",
                timestamp=ended_at,
                payload={
                    "graph_id": definition.graph_id,
                    "graph_version": definition.version,
                    "duration_ms": duration_ms,
                    "output_chars": len(output),
                },
            )
        )

        return output, StageExecutionTrace(
            stage=stage.stage_id,
            prompt_id=prompt.prompt_id,
            prompt_hash=prompt.sha256,
            llm_profile=profile.profile_id,
            llm_provider=profile.provider,
            llm_model=profile.model,
            status="success",
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
        )

    def _build_prompt_variables(self, state: CvGenerationState) -> dict[str, str]:
        variables: dict[str, str] = {
            "cv_text": state["cv_text"],
            "job_description": state["job_description"],
            "latest_cv": state["latest_cv"],
            "previous_cv": state["latest_cv"],
            "orientation_json": state["orientation_json"],
            "orientation_rationale": state["orientation"].rationale,
            "graph_id": state["graph_id"],
            "graph_version": state["graph_version"],
        }

        for stage_id, value in state["stage_outputs"].items():
            variables[f"stage_{stage_id}"] = value

        return variables

    def _render_prompt(self, template: str, variables: dict[str, str]) -> str:
        try:
            return template.format(**variables)
        except KeyError as exc:
            missing = str(exc).strip("'")
            raise PromptResolutionError(f"Missing prompt variable: {missing}") from exc


def _parse_orientation(raw_output: str) -> OrientationDecision:
    parsed = _extract_json(raw_output)
    if not isinstance(parsed, dict):
        return OrientationDecision(
            ats_weight=0.34,
            recruiter_weight=0.33,
            technical_weight=0.33,
            rationale="Fallback orientation used because parsing failed.",
        )

    ats = _coerce_weight(parsed.get("ats_weight"), 0.34)
    recruiter = _coerce_weight(parsed.get("recruiter_weight"), 0.33)
    technical = _coerce_weight(parsed.get("technical_weight"), 0.33)

    total = max(ats + recruiter + technical, 1e-6)
    ats = round(ats / total, 3)
    recruiter = round(recruiter / total, 3)
    technical = round(technical / total, 3)

    rationale = parsed.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = "Orientation inferred from CV and job description."

    return OrientationDecision(
        ats_weight=ats,
        recruiter_weight=recruiter,
        technical_weight=technical,
        rationale=rationale.strip(),
    )


def _extract_json(raw_output: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw_output, flags=re.DOTALL)
    if match is None:
        return None

    snippet = match.group(0)
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def _coerce_weight(value: object, default: float) -> float:
    if isinstance(value, (int, float)):
        normalized = float(value)
        if normalized < 0:
            return 0.0
        return normalized
    return default


def _utc_now() -> datetime:
    return datetime.now(UTC)
