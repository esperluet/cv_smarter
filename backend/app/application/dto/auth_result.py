from dataclasses import dataclass

from app.domain.models.user import User


@dataclass(frozen=True)
class AuthResult:
    user: User
    access_token: str
    refresh_token: str
    token_type: str
    expires_in_seconds: int
