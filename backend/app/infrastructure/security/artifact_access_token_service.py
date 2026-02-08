from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError


@dataclass(frozen=True)
class ArtifactAccessPayload:
    user_id: str
    storage_path: str
    expires_at: datetime


class ArtifactAccessTokenService:
    def __init__(self, *, secret_key: str, algorithm: str, ttl_seconds: int) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._ttl_seconds = ttl_seconds

    def create_token(self, *, user_id: str, storage_path: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._ttl_seconds)
        payload = {
            "sub": user_id,
            "path": storage_path,
            "scope": "artifact_download",
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> ArtifactAccessPayload:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except InvalidTokenError as exc:
            raise ValueError("Invalid artifact token") from exc

        scope = payload.get("scope")
        user_id = payload.get("sub")
        storage_path = payload.get("path")
        exp = payload.get("exp")
        if scope != "artifact_download" or not user_id or not storage_path or not exp:
            raise ValueError("Invalid artifact token")

        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        return ArtifactAccessPayload(
            user_id=str(user_id),
            storage_path=str(storage_path),
            expires_at=expires_at,
        )
