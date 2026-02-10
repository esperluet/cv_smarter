from app.application.dto.auth_result import AuthResult
from app.application.errors import InvalidCredentialsError
from app.core.security import expires_at_from_days
from app.domain.repositories.refresh_session_repository import RefreshSessionRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.password_hasher import PasswordHasher
from app.domain.services.token_service import TokenService


class SignInUseCase:
    def __init__(
        self,
        users: UserRepository,
        sessions: RefreshSessionRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        refresh_token_expire_days: int,
        access_token_expire_minutes: int,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._refresh_token_expire_days = refresh_token_expire_days
        self._access_token_expire_minutes = access_token_expire_minutes

    def execute(self, email: str, password: str) -> AuthResult:
        normalized_email = email.strip().lower()
        user = self._users.get_by_email(normalized_email)

        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid credentials")

        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        access_token, _ = self._token_service.create_access_token(user_id=user.id, role=user.role)
        refresh_token = self._token_service.generate_refresh_token()
        refresh_token_hash = self._token_service.hash_refresh_token(refresh_token)
        refresh_expires_at = expires_at_from_days(self._refresh_token_expire_days)
        self._sessions.create(user_id=user.id, token_hash=refresh_token_hash, expires_at=refresh_expires_at)

        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in_seconds=self._access_token_expire_minutes * 60,
        )
