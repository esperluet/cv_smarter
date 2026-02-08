from app.core.security import utc_now
from app.domain.repositories.refresh_session_repository import RefreshSessionRepository
from app.domain.services.token_service import TokenService


class SignOutUseCase:
    def __init__(self, sessions: RefreshSessionRepository, token_service: TokenService) -> None:
        self._sessions = sessions
        self._token_service = token_service

    def execute(self, refresh_token: str) -> None:
        token_hash = self._token_service.hash_refresh_token(refresh_token)
        self._sessions.revoke(token_hash=token_hash, revoked_at=utc_now())
