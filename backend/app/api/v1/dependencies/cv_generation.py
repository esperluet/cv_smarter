from functools import lru_cache

from app.api.v1.dependencies.document_pipeline import get_document_pipeline_use_case
from app.application.errors import CvGenerationConfigurationError
from app.application.use_cases.generate_targeted_cv import GenerateTargetedCvUseCase
from app.core.settings import settings
from app.infrastructure.langgraph.config import load_cv_generation_runtime_config
from app.infrastructure.llm.configurable_llm_gateway import ConfigurableLLMGateway
from app.infrastructure.prompts.filesystem_prompt_repository import FilesystemPromptRepository
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.infrastructure.tracing.local_jsonl_trace_store import LocalJsonlTraceStore


@lru_cache(maxsize=1)
def get_cv_generation_use_case() -> GenerateTargetedCvUseCase:
    storage = LocalFileStorage(upload_dir=settings.upload_dir)
    orchestrator = get_cv_generation_orchestrator()

    return GenerateTargetedCvUseCase(
        storage=storage,
        max_upload_size_bytes=settings.max_upload_size_bytes,
        document_pipeline=get_document_pipeline_use_case(),
        orchestrator=orchestrator,
        max_job_description_chars=settings.cv_generation_max_job_description_chars,
        preserve_failed_uploads=settings.preserve_failed_uploads,
    )


@lru_cache(maxsize=1)
def get_cv_generation_orchestrator():
    try:
        from app.infrastructure.langgraph.cv_generation_graph import LangGraphCvGenerationOrchestrator
    except ImportError as exc:  # pragma: no cover - explicit runtime failure path
        raise CvGenerationConfigurationError(
            "LangGraph is not installed. Install dependencies before using CV generation graph."
        ) from exc

    config = load_cv_generation_runtime_config(
        providers_path=settings.cv_generation_providers_config_path,
        profiles_path=settings.cv_generation_profiles_config_path,
        graph_index_path=settings.cv_generation_graph_index_config_path,
    )
    llm_gateway = ConfigurableLLMGateway(providers=config.providers)
    prompt_repository = FilesystemPromptRepository(settings.cv_generation_prompts_dir)
    trace_store = LocalJsonlTraceStore(settings.cv_generation_trace_dir)

    return LangGraphCvGenerationOrchestrator(
        config=config,
        llm_gateway=llm_gateway,
        prompt_repository=prompt_repository,
        trace_store=trace_store,
    )
