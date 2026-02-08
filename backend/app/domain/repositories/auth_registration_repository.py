from datetime import datetime
from typing import Protocol

from app.domain.models.user import User


class DuplicateEmailError(Exception):
    pass


class AuthRegistrationRepository(Protocol):
    def register_user_with_refresh_session(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str | None,
        last_name: str | None,
        refresh_token_hash: str,
        refresh_expires_at: datetime,
    ) -> User:
        ...
