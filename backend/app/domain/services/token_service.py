from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: str
    role: str
    expires_at: datetime


class TokenService(Protocol):
    def create_access_token(self, user_id: str, role: str) -> tuple[str, datetime]:
        ...

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        ...

    def generate_refresh_token(self) -> str:
        ...

    def hash_refresh_token(self, refresh_token: str) -> str:
        ...
