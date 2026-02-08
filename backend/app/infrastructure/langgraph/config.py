from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.application.errors import CvGenerationConfigurationError


SUPPORTED_PROVIDER_KINDS = {
    "mock",
    "langchain_openai",
    "langchain_openai_compatible",
    "langchain_anthropic",
    "langchain_deepseek",
}

SUPPORTED_STAGE_ROLES = {
    "orientation",
    "rewrite",
    "final",
    "generic",
}


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    kind: str
    base_url: str | None = None
    api_key_env: str | None = None
    organization: str | None = None
    default_headers: dict[str, str] | None = None
    default_query: dict[str, str] | None = None
    extra_body: dict[str, Any] | None = None
    timeout_seconds: float = 45.0


@dataclass(frozen=True)
class LLMProfileConfig:
    profile_id: str
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int | None = None


@dataclass(frozen=True)
class GraphStageConfig:
    stage_id: str
    role: str
    prompt_id: str
    llm_profile: str
    response_format: str = "text"
    update_latest_cv: bool = False


@dataclass(frozen=True)
class GraphDefinitionConfig:
    graph_id: str
    version: str
    stages: list[GraphStageConfig]
    orientation_stage_id: str | None = None
    final_stage_id: str | None = None

    def get_stage(self, stage_id: str) -> GraphStageConfig:
        for stage in self.stages:
            if stage.stage_id == stage_id:
                return stage
        raise CvGenerationConfigurationError(f"Graph '{self.graph_id}' missing stage '{stage_id}'")


@dataclass(frozen=True)
class GraphRegistryConfig:
    default_graph_id: str
    graphs: dict[str, GraphDefinitionConfig]

    def resolve(self, graph_id: str | None = None) -> GraphDefinitionConfig:
        selected = graph_id or self.default_graph_id
        graph = self.graphs.get(selected)
        if graph is None:
            raise CvGenerationConfigurationError(f"Unknown graph id: {selected}")
        return graph


@dataclass(frozen=True)
class CvGenerationRuntimeConfig:
    providers: dict[str, ProviderConfig]
    llm_profiles: dict[str, LLMProfileConfig]
    graph_registry: GraphRegistryConfig

    def get_provider(self, provider_id: str) -> ProviderConfig:
        provider = self.providers.get(provider_id)
        if provider is None:
            raise CvGenerationConfigurationError(f"Unknown provider id: {provider_id}")
        return provider

    def get_profile(self, profile_id: str) -> LLMProfileConfig:
        profile = self.llm_profiles.get(profile_id)
        if profile is None:
            raise CvGenerationConfigurationError(f"Unknown llm profile id: {profile_id}")
        return profile

    def resolve_graph(self, graph_id: str | None = None) -> GraphDefinitionConfig:
        return self.graph_registry.resolve(graph_id)


def load_cv_generation_runtime_config(
    *,
    providers_path: str | Path,
    profiles_path: str | Path,
    graph_index_path: str | Path,
) -> CvGenerationRuntimeConfig:
    providers = _load_providers(providers_path)
    llm_profiles = _load_llm_profiles(profiles_path)
    graph_registry = _load_graph_registry(graph_index_path)

    _validate_runtime_refs(
        providers=providers,
        llm_profiles=llm_profiles,
        graph_registry=graph_registry,
    )

    return CvGenerationRuntimeConfig(
        providers=providers,
        llm_profiles=llm_profiles,
        graph_registry=graph_registry,
    )


def _load_providers(path: str | Path) -> dict[str, ProviderConfig]:
    payload = _load_yaml_object(path, "providers config")
    providers_payload = payload.get("providers")
    if not isinstance(providers_payload, dict) or not providers_payload:
        raise CvGenerationConfigurationError("Providers config must include non-empty 'providers'")

    return {
        provider_id: _parse_provider(provider_id, raw)
        for provider_id, raw in providers_payload.items()
    }


def _load_llm_profiles(path: str | Path) -> dict[str, LLMProfileConfig]:
    payload = _load_yaml_object(path, "llm profiles config")
    profiles_payload = payload.get("llm_profiles")
    if not isinstance(profiles_payload, dict) or not profiles_payload:
        raise CvGenerationConfigurationError("LLM profiles config must include non-empty 'llm_profiles'")

    return {
        profile_id: _parse_profile(profile_id, raw)
        for profile_id, raw in profiles_payload.items()
    }


def _load_graph_registry(path: str | Path) -> GraphRegistryConfig:
    index_path = Path(path)
    payload = _load_yaml_object(index_path, "graph index config")

    default_graph_id = _expect_non_empty_string(payload.get("default_graph_id"), "default_graph_id")
    graphs_payload = payload.get("graphs")
    if not isinstance(graphs_payload, dict) or not graphs_payload:
        raise CvGenerationConfigurationError("Graph index config must include non-empty 'graphs'")

    graphs: dict[str, GraphDefinitionConfig] = {}
    for graph_id, graph_ref in graphs_payload.items():
        if not isinstance(graph_ref, dict):
            raise CvGenerationConfigurationError(f"Graph index entry '{graph_id}' must be an object")

        relative_file = _expect_non_empty_string(graph_ref.get("file"), f"Graph index '{graph_id}' file")
        graph_file = (index_path.parent / relative_file).resolve()
        graph = _load_graph_definition(graph_file, graph_id)
        graphs[graph_id] = graph

    if default_graph_id not in graphs:
        raise CvGenerationConfigurationError(
            f"default_graph_id '{default_graph_id}' not found in graph index"
        )

    return GraphRegistryConfig(default_graph_id=default_graph_id, graphs=graphs)


def _load_graph_definition(path: Path, expected_graph_id: str) -> GraphDefinitionConfig:
    payload = _load_yaml_object(path, f"graph definition '{expected_graph_id}'")

    graph_id = _expect_non_empty_string(payload.get("graph_id", expected_graph_id), "graph_id")
    if graph_id != expected_graph_id:
        raise CvGenerationConfigurationError(
            f"Graph file '{path}' graph_id '{graph_id}' must match index key '{expected_graph_id}'"
        )

    version = _expect_non_empty_string(payload.get("version", "1"), f"graph '{graph_id}' version")

    stages_payload = payload.get("stages")
    if not isinstance(stages_payload, list) or not stages_payload:
        raise CvGenerationConfigurationError(f"Graph '{graph_id}' must define non-empty 'stages' list")

    stages: list[GraphStageConfig] = []
    seen_ids: set[str] = set()
    for raw in stages_payload:
        stage = _parse_graph_stage(raw, graph_id)
        if stage.stage_id in seen_ids:
            raise CvGenerationConfigurationError(
                f"Graph '{graph_id}' has duplicate stage id '{stage.stage_id}'"
            )
        seen_ids.add(stage.stage_id)
        stages.append(stage)

    orientation_stage_id = _optional_non_empty_string(payload.get("orientation_stage_id"))
    final_stage_id = _optional_non_empty_string(payload.get("final_stage_id"))

    if orientation_stage_id and orientation_stage_id not in seen_ids:
        raise CvGenerationConfigurationError(
            f"Graph '{graph_id}' references unknown orientation_stage_id '{orientation_stage_id}'"
        )
    if final_stage_id and final_stage_id not in seen_ids:
        raise CvGenerationConfigurationError(
            f"Graph '{graph_id}' references unknown final_stage_id '{final_stage_id}'"
        )

    return GraphDefinitionConfig(
        graph_id=graph_id,
        version=version,
        stages=stages,
        orientation_stage_id=orientation_stage_id,
        final_stage_id=final_stage_id,
    )


def _parse_graph_stage(payload: Any, graph_id: str) -> GraphStageConfig:
    if not isinstance(payload, dict):
        raise CvGenerationConfigurationError(f"Graph '{graph_id}' stage entries must be objects")

    stage_id = _expect_stage_id(payload.get("id"), f"Graph '{graph_id}' stage id")
    role = _expect_non_empty_string(payload.get("role", "generic"), f"Graph '{graph_id}' stage role")
    if role not in SUPPORTED_STAGE_ROLES:
        raise CvGenerationConfigurationError(
            f"Graph '{graph_id}' stage '{stage_id}' role '{role}' is not supported"
        )

    prompt_id = _expect_non_empty_string(payload.get("prompt_id"), f"Graph '{graph_id}' stage '{stage_id}' prompt_id")
    llm_profile = _expect_non_empty_string(
        payload.get("llm_profile"),
        f"Graph '{graph_id}' stage '{stage_id}' llm_profile",
    )

    response_format = str(payload.get("response_format", "text"))
    if response_format not in {"text", "json"}:
        raise CvGenerationConfigurationError(
            f"Graph '{graph_id}' stage '{stage_id}' response_format must be 'text' or 'json'"
        )

    update_latest_cv_raw = payload.get("update_latest_cv")
    if update_latest_cv_raw is None:
        update_latest_cv = role in {"rewrite", "final"}
    elif isinstance(update_latest_cv_raw, bool):
        update_latest_cv = update_latest_cv_raw
    else:
        raise CvGenerationConfigurationError(
            f"Graph '{graph_id}' stage '{stage_id}' update_latest_cv must be a boolean"
        )

    return GraphStageConfig(
        stage_id=stage_id,
        role=role,
        prompt_id=prompt_id,
        llm_profile=llm_profile,
        response_format=response_format,
        update_latest_cv=update_latest_cv,
    )


def _parse_provider(provider_id: str, payload: Any) -> ProviderConfig:
    if not isinstance(payload, dict):
        raise CvGenerationConfigurationError(f"Provider '{provider_id}' must be an object")

    kind = _expect_non_empty_string(payload.get("kind"), f"Provider '{provider_id}' kind")
    if kind not in SUPPORTED_PROVIDER_KINDS:
        raise CvGenerationConfigurationError(
            f"Provider '{provider_id}' kind '{kind}' is not supported. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_PROVIDER_KINDS))}"
        )

    base_url = _optional_non_empty_string(payload.get("base_url"))
    api_key_env = _optional_non_empty_string(payload.get("api_key_env"))
    organization = _optional_non_empty_string(payload.get("organization"))
    default_headers = _optional_string_dict(payload.get("default_headers"))
    default_query = _optional_string_dict(payload.get("default_query"))
    extra_body = _optional_mapping(payload.get("extra_body"))
    timeout_seconds = float(payload.get("timeout_seconds", 45.0))

    if kind == "langchain_openai_compatible" and not base_url:
        raise CvGenerationConfigurationError(
            f"Provider '{provider_id}' with kind '{kind}' must define 'base_url'"
        )

    return ProviderConfig(
        provider_id=provider_id,
        kind=kind,
        base_url=base_url,
        api_key_env=api_key_env,
        organization=organization,
        default_headers=default_headers,
        default_query=default_query,
        extra_body=extra_body,
        timeout_seconds=timeout_seconds,
    )


def _parse_profile(profile_id: str, payload: Any) -> LLMProfileConfig:
    if not isinstance(payload, dict):
        raise CvGenerationConfigurationError(f"LLM profile '{profile_id}' must be an object")

    provider = _expect_non_empty_string(payload.get("provider"), f"LLM profile '{profile_id}' provider")
    model = _expect_non_empty_string(payload.get("model"), f"LLM profile '{profile_id}' model")
    temperature = float(payload.get("temperature", 0.2))

    max_tokens_raw = payload.get("max_tokens")
    max_tokens = int(max_tokens_raw) if max_tokens_raw is not None else None

    return LLMProfileConfig(
        profile_id=profile_id,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _validate_runtime_refs(
    *,
    providers: dict[str, ProviderConfig],
    llm_profiles: dict[str, LLMProfileConfig],
    graph_registry: GraphRegistryConfig,
) -> None:
    for profile in llm_profiles.values():
        if profile.provider not in providers:
            raise CvGenerationConfigurationError(
                f"LLM profile '{profile.profile_id}' references unknown provider '{profile.provider}'"
            )

    for graph in graph_registry.graphs.values():
        for stage in graph.stages:
            if stage.llm_profile not in llm_profiles:
                raise CvGenerationConfigurationError(
                    f"Graph '{graph.graph_id}' stage '{stage.stage_id}' references unknown llm_profile "
                    f"'{stage.llm_profile}'"
                )


def _load_yaml_object(path: str | Path, label: str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise CvGenerationConfigurationError(f"{label} file does not exist: {config_path}")

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CvGenerationConfigurationError(f"{label} must be a YAML object")

    return payload


def _expect_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CvGenerationConfigurationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _expect_stage_id(value: Any, field_name: str) -> str:
    stage_id = _expect_non_empty_string(value, field_name)
    if not stage_id.replace("_", "").isalnum():
        raise CvGenerationConfigurationError(
            f"{field_name} must use only alphanumeric characters and underscores"
        )
    return stage_id


def _optional_non_empty_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _optional_string_dict(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise CvGenerationConfigurationError("Expected a mapping with string keys/values")

    normalized: dict[str, str] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, str):
            raise CvGenerationConfigurationError("Expected a mapping with string keys/values")
        normalized[key] = raw
    return normalized


def _optional_mapping(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise CvGenerationConfigurationError("Expected an object mapping")
    return value
