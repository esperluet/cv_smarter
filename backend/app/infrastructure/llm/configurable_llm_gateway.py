import json
import os
from typing import Any

from app.application.errors import CvGenerationExecutionError
from app.domain.services.llm_gateway import LLMGateway, LLMRequest
from app.infrastructure.langgraph.config import ProviderConfig


class ConfigurableLLMGateway(LLMGateway):
    def __init__(self, providers: dict[str, ProviderConfig]) -> None:
        self._providers = providers
        self._model_cache: dict[tuple[str, str, str, float, int | None], Any] = {}

    def generate(self, request: LLMRequest) -> str:
        provider = self._providers.get(request.provider)
        if provider is None:
            raise CvGenerationExecutionError(f"Unknown provider '{request.provider}'")

        if provider.kind == "mock":
            return self._generate_mock_response(request)

        model = self._get_or_create_model(provider=provider, request=request)
        run_config = {
            "run_name": f"cv_generation.{request.stage}",
            "tags": ["cv_generation", f"stage:{request.stage}", f"provider:{provider.provider_id}"],
            "metadata": {
                "stage": request.stage,
                "provider_id": provider.provider_id,
                "provider_kind": provider.kind,
                "model": request.model,
            },
        }

        try:
            response = model.invoke(request.prompt, config=run_config)
        except Exception as exc:
            raise CvGenerationExecutionError(
                f"LLM request failed for stage '{request.stage}' with provider '{provider.provider_id}'"
            ) from exc

        content = _extract_message_text(response)
        if not content.strip():
            raise CvGenerationExecutionError(
                f"LLM returned empty content for stage '{request.stage}'"
            )
        return content

    def _get_or_create_model(self, *, provider: ProviderConfig, request: LLMRequest) -> Any:
        cache_key = (
            provider.provider_id,
            provider.kind,
            request.model,
            request.temperature,
            request.max_tokens,
        )
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        model = self._build_model(provider=provider, request=request)
        self._model_cache[cache_key] = model
        return model

    def _build_model(self, *, provider: ProviderConfig, request: LLMRequest) -> Any:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError as exc:  # pragma: no cover - explicit runtime failure path
            raise CvGenerationExecutionError(
                "langchain is not installed. Install dependencies to use non-mock LLM providers."
            ) from exc

        base_kwargs: dict[str, Any] = {
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            base_kwargs["max_tokens"] = request.max_tokens
        timeout = request.timeout_seconds or provider.timeout_seconds
        if timeout:
            base_kwargs["timeout"] = timeout

        api_key = _resolve_api_key(provider)
        if api_key is not None:
            base_kwargs["api_key"] = api_key

        if provider.kind == "langchain_openai":
            return init_chat_model(
                request.model,
                model_provider="openai",
                **_merge_openai_kwargs(base_kwargs, provider),
            )

        if provider.kind == "langchain_openai_compatible":
            if not provider.base_url:
                raise CvGenerationExecutionError(
                    f"Provider '{provider.provider_id}' must define base_url for openai-compatible mode"
                )
            return init_chat_model(
                request.model,
                model_provider="openai",
                **_merge_openai_kwargs(base_kwargs, provider),
            )

        if provider.kind == "langchain_anthropic":
            return init_chat_model(
                request.model,
                model_provider="anthropic",
                **base_kwargs,
            )

        if provider.kind == "langchain_deepseek":
            return init_chat_model(
                request.model,
                model_provider="deepseek",
                **_merge_deepseek_kwargs(base_kwargs, provider),
            )

        raise CvGenerationExecutionError(
            f"Unsupported provider kind '{provider.kind}' for provider '{provider.provider_id}'"
        )

    def _generate_mock_response(self, request: LLMRequest) -> str:
        if request.stage == "determine_orientation":
            return json.dumps(
                {
                    "ats_weight": 0.35,
                    "recruiter_weight": 0.30,
                    "technical_weight": 0.35,
                    "rationale": "Balanced default profile for readability, ATS parsing, and technical depth.",
                }
            )

        if request.stage == "ats_pass":
            return "ATS-optimized CV draft\n\n" + request.prompt[:2000]

        if request.stage == "recruiter_pass":
            return "Recruiter-focused CV draft\n\n" + request.prompt[:2000]

        if request.stage == "technical_pass":
            return "Technical-expert CV draft\n\n" + request.prompt[:2000]

        if request.stage == "final_render":
            return "Final CV\n\n" + request.prompt[:3000]

        return request.prompt[:2000]


def _resolve_api_key(provider: ProviderConfig) -> str | None:
    if not provider.api_key_env:
        return None

    value = os.getenv(provider.api_key_env, "").strip()
    if not value:
        raise CvGenerationExecutionError(
            f"Provider '{provider.provider_id}' API key env variable '{provider.api_key_env}' is missing or empty"
        )
    return value


def _merge_openai_kwargs(base_kwargs: dict[str, Any], provider: ProviderConfig) -> dict[str, Any]:
    merged = dict(base_kwargs)
    if provider.base_url:
        merged["base_url"] = provider.base_url
    if provider.organization:
        merged["organization"] = provider.organization
    if provider.default_headers:
        merged["default_headers"] = provider.default_headers
    if provider.default_query:
        merged["default_query"] = provider.default_query
    if provider.extra_body:
        merged["extra_body"] = provider.extra_body
    return merged


def _merge_deepseek_kwargs(base_kwargs: dict[str, Any], provider: ProviderConfig) -> dict[str, Any]:
    merged = dict(base_kwargs)
    if provider.base_url:
        merged["base_url"] = provider.base_url
    return merged


def _extract_message_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    return str(content) if content is not None else ""
