from app.application.dto.auth_result import AuthResult
from app.application.errors import InvalidRefreshTokenError, UserNotFoundError
from app.core.security import expires_at_from_days, utc_now
from app.domain.repositories.refresh_session_repository import RefreshSessionRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.token_service import TokenService


class RefreshSessionUseCase:
    def __init__(
        self,
        users: UserRepository,
        sessions: RefreshSessionRepository,
        token_service: TokenService,
        refresh_token_expire_days: int,
        access_token_expire_minutes: int,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._token_service = token_service
        self._refresh_token_expire_days = refresh_token_expire_days
        self._access_token_expire_minutes = access_token_expire_minutes

    def execute(self, refresh_token: str) -> AuthResult:
        token_hash = self._token_service.hash_refresh_token(refresh_token)
        current_session = self._sessions.get_valid(token_hash=token_hash, now=utc_now())
        if current_session is None:
            raise InvalidRefreshTokenError("Invalid refresh token")

        user = self._users.get_by_id(current_session.user_id)
        if user is None or not user.is_active:
            raise UserNotFoundError("User not found")

        access_token, _ = self._token_service.create_access_token(user_id=user.id, role=user.role)
        new_refresh_token = self._token_service.generate_refresh_token()
        new_refresh_hash = self._token_service.hash_refresh_token(new_refresh_token)
        refresh_expires_at = expires_at_from_days(self._refresh_token_expire_days)

        rotated = self._sessions.rotate(
            old_token_hash=token_hash,
            new_token_hash=new_refresh_hash,
            expires_at=refresh_expires_at,
            now=utc_now(),
        )
        if rotated is None:
            raise InvalidRefreshTokenError("Invalid refresh token")

        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in_seconds=self._access_token_expire_minutes * 60,
        )
