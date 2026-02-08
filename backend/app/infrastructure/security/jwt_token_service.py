import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.domain.services.token_service import AccessTokenPayload


class JWTTokenService:
    def __init__(self, secret_key: str, algorithm: str, access_token_expire_minutes: int) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes

    def create_access_token(self, user_id: str, role: str) -> tuple[str, datetime]:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "role": role,
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        return token, expires_at

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except InvalidTokenError as exc:
            raise ValueError("Invalid access token") from exc

        user_id = payload.get("sub")
        role = payload.get("role")
        exp = payload.get("exp")

        if not user_id or not role or not exp:
            raise ValueError("Invalid access token")

        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        return AccessTokenPayload(user_id=user_id, role=role, expires_at=expires_at)

    def generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def hash_refresh_token(self, refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
