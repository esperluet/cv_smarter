from collections.abc import Generator
from importlib.util import find_spec

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.dependencies.auth import get_db, get_mailer
from app.api.v1.dependencies.cv_generation import get_cv_generation_orchestrator, get_cv_generation_use_case
from app.api.v1.dependencies.document_pipeline import get_document_pipeline_use_case
from app.api.v1.dependencies.cv import get_cv_upload_use_case
from app.api.v1.dependencies.documents import get_artifact_access_token_service
from app.api.v1.dependencies.documents import get_document_upload_use_case
from app.core.database import Base
from app.core.settings import settings
from app.infrastructure.persistence import models  # noqa: F401
from app.main import app


class DummyMailer:
    def __init__(self) -> None:
        self.sent_to: list[str] = []

    def send_welcome_email(self, to_email: str, first_name: str | None) -> None:
        self.sent_to.append(to_email)


def test_auth_account_and_cv_upload_flow(tmp_path) -> None:
    db_file = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    prompts_dir = tmp_path / "prompts" / "cv_rewrite_v1"
    config_dir = tmp_path / "config"
    llm_config_dir = config_dir / "llm"
    graphs_config_dir = config_dir / "graphs"
    traces_dir = tmp_path / "traces"
    upload_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    llm_config_dir.mkdir(parents=True, exist_ok=True)
    graphs_config_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    (prompts_dir / "determine_orientation.md").write_text(
        "{cv_text}\n{job_description}",
        encoding="utf-8",
    )
    (prompts_dir / "ats_pass.md").write_text(
        "{cv_text}\n{job_description}\n{orientation_json}",
        encoding="utf-8",
    )
    (prompts_dir / "recruiter_pass.md").write_text(
        "{previous_cv}\n{job_description}\n{orientation_json}",
        encoding="utf-8",
    )
    (prompts_dir / "technical_pass.md").write_text(
        "{previous_cv}\n{job_description}\n{orientation_json}",
        encoding="utf-8",
    )
    (prompts_dir / "final_render.md").write_text(
        "{previous_cv}\n{job_description}\n{orientation_json}",
        encoding="utf-8",
    )

    (llm_config_dir / "providers.yml").write_text(
        """
providers:
  mock_local:
    kind: mock
""".strip(),
        encoding="utf-8",
    )
    (llm_config_dir / "profiles.yml").write_text(
        """
llm_profiles:
  orientation_default:
    provider: mock_local
    model: mock-orientation
  writer_default:
    provider: mock_local
    model: mock-model
""".strip(),
        encoding="utf-8",
    )
    (graphs_config_dir / "index.yml").write_text(
        """
default_graph_id: cv_rewrite_v1
graphs:
  cv_rewrite_v1:
    file: cv_rewrite_v1.yml
""".strip(),
        encoding="utf-8",
    )
    (graphs_config_dir / "cv_rewrite_v1.yml").write_text(
        """
graph_id: cv_rewrite_v1
version: "1"
orientation_stage_id: determine_orientation
final_stage_id: final_render
stages:
  - id: determine_orientation
    role: orientation
    prompt_id: cv_rewrite_v1/determine_orientation
    llm_profile: orientation_default
    response_format: json
    update_latest_cv: false
  - id: ats_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/ats_pass
    llm_profile: writer_default
  - id: recruiter_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/recruiter_pass
    llm_profile: writer_default
  - id: technical_pass
    role: rewrite
    prompt_id: cv_rewrite_v1/technical_pass
    llm_profile: writer_default
  - id: final_render
    role: final
    prompt_id: cv_rewrite_v1/final_render
    llm_profile: writer_default
""".strip(),
        encoding="utf-8",
    )

    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=test_engine)

    settings.upload_dir = str(upload_dir)
    settings.max_upload_size_bytes = 1024 * 1024
    settings.document_output_formats = "markdown,json"
    settings.document_ingestor_preferred = "fallback"
    settings.cv_generation_providers_config_path = str(llm_config_dir / "providers.yml")
    settings.cv_generation_profiles_config_path = str(llm_config_dir / "profiles.yml")
    settings.cv_generation_graph_index_config_path = str(graphs_config_dir / "index.yml")
    settings.cv_generation_prompts_dir = str(tmp_path / "prompts")
    settings.cv_generation_trace_dir = str(traces_dir)
    settings.artifact_download_mode = "signed"
    settings.artifact_download_token_ttl_seconds = 300
    get_cv_upload_use_case.cache_clear()
    get_cv_generation_orchestrator.cache_clear()
    get_cv_generation_use_case.cache_clear()
    get_document_upload_use_case.cache_clear()
    get_document_pipeline_use_case.cache_clear()
    get_artifact_access_token_service.cache_clear()

    mailer = DummyMailer()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_mailer] = lambda: mailer

    with TestClient(app) as client:
        sign_up_response = client.post(
            "/api/v1/auth/sign-up",
            json={
                "email": "john@example.com",
                "password": "strong-password",
                "first_name": "John",
                "last_name": "Doe",
            },
        )
        assert sign_up_response.status_code == 201
        sign_up_payload = sign_up_response.json()
        assert sign_up_payload["user"]["email"] == "john@example.com"

        duplicate_sign_up_response = client.post(
            "/api/v1/auth/sign-up",
            json={
                "email": "john@example.com",
                "password": "strong-password",
                "first_name": "John",
                "last_name": "Doe",
            },
        )
        assert duplicate_sign_up_response.status_code == 409

        token = sign_up_payload["access_token"]
        assert mailer.sent_to == ["john@example.com"]

        update_response = client.patch(
            "/api/v1/account/me",
            json={"first_name": "Johnny"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        updated_user = update_response.json()["user"]
        assert updated_user["first_name"] == "Johnny"
        assert updated_user["last_name"] == "Doe"

        files = {"file": ("resume.txt", b"John Doe\nEmail: john@example.com\n", "text/plain")}
        upload_response = client.post(
            "/api/v1/cv/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_response.status_code == 200
        upload_payload = upload_response.json()
        assert upload_payload["filename"] == "resume.txt"
        assert upload_payload["metrics"]["emails_detected"] >= 1
        assert len(upload_payload["artifacts"]) == 2
        assert upload_payload["processing_report"]["engine_name"] in {"fallback_text", "docling"}

        source_create_response = client.post(
            "/api/v1/sources",
            data={"name": "Primary Resume"},
            files={"file": ("resume.txt", b"John Doe\nSenior AI Architect", "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert source_create_response.status_code == 201
        source_create_payload = source_create_response.json()
        assert source_create_payload["name"] == "Primary Resume"
        source_id = source_create_payload["id"]

        source_list_response = client.get(
            "/api/v1/sources",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert source_list_response.status_code == 200
        source_list_payload = source_list_response.json()
        assert len(source_list_payload["items"]) == 1
        assert source_list_payload["items"][0]["id"] == source_id

        process_response = client.post(
            "/api/v1/documents/process",
            files={"file": ("resume.txt", b"John Doe\nSenior AI Architect", "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert process_response.status_code == 200
        process_payload = process_response.json()
        assert process_payload["filename"] == "resume.txt"
        assert process_payload["processing_report"]["engine_name"] == "fallback_text"
        assert len(process_payload["artifacts"]) == 2
        assert process_payload["canonical_document"]["source_media_type"] == "text/plain"
        assert process_payload["processing_report"]["quality_score"] is not None

        first_artifact = process_payload["artifacts"][0]
        assert first_artifact["download_token"]
        assert first_artifact["download_url"]
        artifact_download_response = client.get(
            "/api/v1/documents/artifacts/download",
            params={
                "storage_path": first_artifact["storage_path"],
                "token": first_artifact["download_token"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert artifact_download_response.status_code == 200
        assert artifact_download_response.content

        missing_artifact_token_response = client.get(
            "/api/v1/documents/artifacts/download",
            params={"storage_path": first_artifact["storage_path"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing_artifact_token_response.status_code == 400

        second_user_sign_up_response = client.post(
            "/api/v1/auth/sign-up",
            json={
                "email": "jane@example.com",
                "password": "strong-password",
                "first_name": "Jane",
                "last_name": "Roe",
            },
        )
        assert second_user_sign_up_response.status_code == 201
        second_token = second_user_sign_up_response.json()["access_token"]

        cross_user_artifact_response = client.get(
            "/api/v1/documents/artifacts/download",
            params={
                "storage_path": first_artifact["storage_path"],
                "token": first_artifact["download_token"],
            },
            headers={"Authorization": f"Bearer {second_token}"},
        )
        assert cross_user_artifact_response.status_code == 403

        pdf_process_response = client.post(
            "/api/v1/documents/process",
            files={"file": ("resume.pdf", b"%PDF-1.4\nBinary", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pdf_process_response.status_code in {415, 422}

        if find_spec("langgraph") is not None:
            export_pdf_response = client.post(
                "/api/v1/cv/export/pdf",
                json={
                    "content": "# Resume\n\n- Item",
                    "format_hint": "markdown",
                    "filename": "resume_export",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert export_pdf_response.status_code == 200
            assert export_pdf_response.headers["content-type"].startswith("application/pdf")
            assert "filename=\"resume_export.pdf\"" in export_pdf_response.headers.get("content-disposition", "")
            assert export_pdf_response.content.startswith(b"%PDF")

            generate_response = client.post(
                "/api/v1/cv/generate",
                data={"job_description": "Data platform architect", "graph_id": "cv_rewrite_v1"},
                files={"file": ("resume.txt", b"John Doe\nSenior AI Architect", "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert generate_response.status_code == 200
            generate_payload = generate_response.json()
            assert generate_payload["run_id"]
            assert generate_payload["graph_id"] == "cv_rewrite_v1"
            assert generate_payload["graph_version"] == "1"
            assert generate_payload["final_cv"]
            assert generate_payload["orientation"]["rationale"]
            assert len(generate_payload["stage_traces"]) == 5

            generate_from_source_response = client.post(
                "/api/v1/cv/generate-from-source",
                data={
                    "source_id": source_id,
                    "job_description": "Data platform architect",
                    "graph_id": "cv_rewrite_v1",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert generate_from_source_response.status_code == 200
            generate_from_source_payload = generate_from_source_response.json()
            assert generate_from_source_payload["source_id"] == source_id
            assert generate_from_source_payload["graph_id"] == "cv_rewrite_v1"
            assert generate_from_source_payload["final_cv"]
            assert len(generate_from_source_payload["stage_traces"]) == 5

            generate_from_source_pdf_response = client.post(
                "/api/v1/cv/generate-from-source/pdf",
                data={
                    "source_id": source_id,
                    "job_description": "Data platform architect",
                    "graph_id": "cv_rewrite_v1",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert generate_from_source_pdf_response.status_code == 200
            assert generate_from_source_pdf_response.headers["content-type"].startswith("application/pdf")
            assert "filename=" in generate_from_source_pdf_response.headers.get("content-disposition", "")
            assert generate_from_source_pdf_response.content.startswith(b"%PDF")

        source_delete_response = client.delete(
            f"/api/v1/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert source_delete_response.status_code == 204

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
