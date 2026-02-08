import pytest

from app.infrastructure.security.artifact_access_token_service import ArtifactAccessTokenService


def test_artifact_access_token_round_trip() -> None:
    service = ArtifactAccessTokenService(secret_key="test-secret", algorithm="HS256", ttl_seconds=300)

    token = service.create_token(user_id="user_1", storage_path="/tmp/file.md")
    payload = service.verify_token(token)

    assert payload.user_id == "user_1"
    assert payload.storage_path == "/tmp/file.md"


def test_artifact_access_token_rejects_tampering() -> None:
    service = ArtifactAccessTokenService(secret_key="test-secret", algorithm="HS256", ttl_seconds=300)
    token = service.create_token(user_id="user_1", storage_path="/tmp/file.md")
    tampered = f"{token}tampered"

    with pytest.raises(ValueError):
        service.verify_token(tampered)
