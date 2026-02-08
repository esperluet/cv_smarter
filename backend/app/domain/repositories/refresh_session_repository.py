from datetime import datetime
from typing import Protocol

from app.domain.models.refresh_session import RefreshSession


class RefreshSessionRepository(Protocol):
    def create(self, user_id: str, token_hash: str, expires_at: datetime) -> RefreshSession:
        ...

    def get_valid(self, token_hash: str, now: datetime) -> RefreshSession | None:
        ...

    def revoke(self, token_hash: str, revoked_at: datetime) -> bool:
        ...

    def rotate(self, old_token_hash: str, new_token_hash: str, expires_at: datetime, now: datetime) -> RefreshSession | None:
        ...
