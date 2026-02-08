import pytest

from app.application.errors import CvGenerationConfigurationError
from app.infrastructure.langgraph.config import load_cv_generation_runtime_config


def _write_default_files(tmp_path):
    providers_path = tmp_path / "providers.yml"
    profiles_path = tmp_path / "profiles.yml"
    graph_index_path = tmp_path / "index.yml"
    graph_file_path = tmp_path / "cv_rewrite_v1.yml"

    providers_path.write_text(
        """
providers:
  mock_local:
    kind: mock
""".strip(),
        encoding="utf-8",
    )

    profiles_path.write_text(
        """
llm_profiles:
  default:
    provider: mock_local
    model: mock-model
""".strip(),
        encoding="utf-8",
    )

    graph_index_path.write_text(
        """
default_graph_id: cv_rewrite_v1
graphs:
  cv_rewrite_v1:
    file: cv_rewrite_v1.yml
""".strip(),
        encoding="utf-8",
    )

    graph_file_path.write_text(
        """
graph_id: cv_rewrite_v1
version: "1"
orientation_stage_id: determine_orientation
final_stage_id: final_render
stages:
  - id: determine_orientation
    role: orientation
    prompt_id: cv_rewrite_v1/determine_orientation
    llm_profile: default
    response_format: json
  - id: ats_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/ats_pass
    llm_profile: default
  - id: recruiter_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/recruiter_pass
    llm_profile: default
  - id: technical_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/technical_pass
    llm_profile: default
  - id: final_render
    role: final
    prompt_id: cv_rewrite_v1/final_render
    llm_profile: default
""".strip(),
        encoding="utf-8",
    )

    return providers_path, profiles_path, graph_index_path


def test_load_cv_generation_runtime_config_success(tmp_path) -> None:
    providers_path, profiles_path, graph_index_path = _write_default_files(tmp_path)

    config = load_cv_generation_runtime_config(
        providers_path=providers_path,
        profiles_path=profiles_path,
        graph_index_path=graph_index_path,
    )

    graph = config.resolve_graph()
    assert graph.graph_id == "cv_rewrite_v1"
    assert graph.stages[0].stage_id == "determine_orientation"
    assert config.get_profile("default").model == "mock-model"


def test_load_cv_generation_runtime_config_fails_on_missing_stage_list(tmp_path) -> None:
    providers_path = tmp_path / "providers.yml"
    profiles_path = tmp_path / "profiles.yml"
    graph_index_path = tmp_path / "index.yml"
    graph_file_path = tmp_path / "cv_rewrite_v1.yml"

    providers_path.write_text("providers:\n  mock_local:\n    kind: mock\n", encoding="utf-8")
    profiles_path.write_text(
        "llm_profiles:\n  default:\n    provider: mock_local\n    model: mock-model\n",
        encoding="utf-8",
    )
    graph_index_path.write_text(
        "default_graph_id: cv_rewrite_v1\ngraphs:\n  cv_rewrite_v1:\n    file: cv_rewrite_v1.yml\n",
        encoding="utf-8",
    )
    graph_file_path.write_text("graph_id: cv_rewrite_v1\nversion: '1'\n", encoding="utf-8")

    with pytest.raises(CvGenerationConfigurationError):
        load_cv_generation_runtime_config(
            providers_path=providers_path,
            profiles_path=profiles_path,
            graph_index_path=graph_index_path,
        )


def test_load_cv_generation_runtime_config_fails_on_unsupported_provider_kind(tmp_path) -> None:
    providers_path = tmp_path / "providers.yml"
    profiles_path = tmp_path / "profiles.yml"
    graph_index_path = tmp_path / "index.yml"
    graph_file_path = tmp_path / "cv_rewrite_v1.yml"

    providers_path.write_text(
        "providers:\n  invalid_provider:\n    kind: custom_http\n",
        encoding="utf-8",
    )
    profiles_path.write_text(
        "llm_profiles:\n  default:\n    provider: invalid_provider\n    model: fake-model\n",
        encoding="utf-8",
    )
    graph_index_path.write_text(
        "default_graph_id: cv_rewrite_v1\ngraphs:\n  cv_rewrite_v1:\n    file: cv_rewrite_v1.yml\n",
        encoding="utf-8",
    )
    graph_file_path.write_text(
        """
graph_id: cv_rewrite_v1
version: "1"
stages:
  - id: determine_orientation
    role: orientation
    prompt_id: cv_rewrite_v1/determine_orientation
    llm_profile: default
  - id: ats_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/ats_pass
    llm_profile: default
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(CvGenerationConfigurationError):
        load_cv_generation_runtime_config(
            providers_path=providers_path,
            profiles_path=profiles_path,
            graph_index_path=graph_index_path,
        )
