import pytest

from app.application.errors import CvGenerationExecutionError
from app.domain.services.llm_gateway import LLMRequest
from app.infrastructure.langgraph.config import ProviderConfig
from app.infrastructure.llm.configurable_llm_gateway import ConfigurableLLMGateway


class DummyModel:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[tuple[object, object]] = []

    def invoke(self, prompt, config=None):
        self.calls.append((prompt, config))
        return type("DummyResponse", (), {"content": self._content})()


def test_mock_provider_returns_deterministic_output() -> None:
    gateway = ConfigurableLLMGateway(
        providers={
            "mock": ProviderConfig(provider_id="mock", kind="mock"),
        }
    )

    result = gateway.generate(
        LLMRequest(
            stage="determine_orientation",
            provider="mock",
            model="mock-model",
            prompt="hello",
        )
    )

    assert '"ats_weight"' in result


def test_openai_compatible_provider_uses_langchain_init(monkeypatch) -> None:
    captured: dict[str, object] = {}
    model = DummyModel(content="rewritten cv")

    def fake_init_chat_model(model_name, *, model_provider, **kwargs):
        captured["model_name"] = model_name
        captured["model_provider"] = model_provider
        captured["kwargs"] = kwargs
        return model

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)
    monkeypatch.setenv("TEST_OPENAI_KEY", "secret")

    gateway = ConfigurableLLMGateway(
        providers={
            "openai_compatible": ProviderConfig(
                provider_id="openai_compatible",
                kind="langchain_openai_compatible",
                base_url="https://example.com/v1",
                api_key_env="TEST_OPENAI_KEY",
                timeout_seconds=12,
                extra_body={"reasoning": {"effort": "medium"}},
            ),
        }
    )

    result = gateway.generate(
        LLMRequest(
            stage="ats_pass",
            provider="openai_compatible",
            model="openai/gpt-4o-mini",
            prompt="Rewrite this CV",
            temperature=0.2,
            max_tokens=512,
        )
    )

    assert result == "rewritten cv"
    assert captured["model_provider"] == "openai"
    assert captured["model_name"] == "openai/gpt-4o-mini"
    kwargs = captured["kwargs"]
    assert kwargs["api_key"] == "secret"
    assert kwargs["base_url"] == "https://example.com/v1"
    assert kwargs["extra_body"] == {"reasoning": {"effort": "medium"}}
    assert kwargs["max_tokens"] == 512
    assert kwargs["timeout"] == 12


def test_missing_api_key_raises_error() -> None:
    gateway = ConfigurableLLMGateway(
        providers={
            "anthropic": ProviderConfig(
                provider_id="anthropic",
                kind="langchain_anthropic",
                api_key_env="MISSING_TEST_KEY",
            ),
        }
    )

    with pytest.raises(CvGenerationExecutionError):
        gateway.generate(
            LLMRequest(
                stage="technical_pass",
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                prompt="Improve technical depth",
            )
        )
