from app.application.dto.auth_result import AuthResult
from app.application.errors import EmailAlreadyExistsError
from app.core.security import expires_at_from_days
from app.core.settings import settings
from app.domain.repositories.auth_registration_repository import AuthRegistrationRepository, DuplicateEmailError
from app.domain.services.mailer import Mailer
from app.domain.services.password_hasher import PasswordHasher
from app.domain.services.token_service import TokenService


class SignUpUseCase:
    def __init__(
        self,
        registration: AuthRegistrationRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        mailer: Mailer,
    ) -> None:
        self._registration = registration
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._mailer = mailer

    def execute(self, email: str, password: str, first_name: str | None, last_name: str | None) -> AuthResult:
        normalized_email = email.strip().lower()
        password_hash = self._password_hasher.hash(password)

        refresh_token = self._token_service.generate_refresh_token()
        refresh_token_hash = self._token_service.hash_refresh_token(refresh_token)
        refresh_expires_at = expires_at_from_days(settings.refresh_token_expire_days)
        try:
            user = self._registration.register_user_with_refresh_session(
                email=normalized_email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                refresh_token_hash=refresh_token_hash,
                refresh_expires_at=refresh_expires_at,
            )
        except DuplicateEmailError as exc:
            raise EmailAlreadyExistsError("Email is already registered") from exc
        access_token, _ = self._token_service.create_access_token(user_id=user.id, role=user.role)

        try:
            self._mailer.send_welcome_email(to_email=user.email, first_name=user.first_name)
        except Exception:
            # Signup remains successful even if email delivery fails.
            pass

        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in_seconds=settings.access_token_expire_minutes * 60,
        )
