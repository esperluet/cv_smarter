from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.settings import settings
from app.infrastructure.mailer.smtp_mailer import SMTPMailer
from app.infrastructure.repositories.sqlalchemy_auth_registration_repository import SQLAlchemyAuthRegistrationRepository
from app.infrastructure.repositories.sqlalchemy_refresh_session_repository import SQLAlchemyRefreshSessionRepository
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.infrastructure.security.bcrypt_password_hasher import PBKDF2PasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService

security_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    role: str


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_user_repository(db: Annotated[Session, Depends(get_db)]) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db)


def get_auth_registration_repository(
    db: Annotated[Session, Depends(get_db)],
) -> SQLAlchemyAuthRegistrationRepository:
    return SQLAlchemyAuthRegistrationRepository(db)


def get_refresh_session_repository(db: Annotated[Session, Depends(get_db)]) -> SQLAlchemyRefreshSessionRepository:
    return SQLAlchemyRefreshSessionRepository(db)


def get_password_hasher() -> PBKDF2PasswordHasher:
    return PBKDF2PasswordHasher()


def get_token_service() -> JWTTokenService:
    return JWTTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
    )


def get_mailer() -> SMTPMailer:
    return SMTPMailer(
        host=settings.smtp_host,
        port=settings.smtp_port,
        from_email=settings.smtp_from_email,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    users: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    token_service: Annotated[JWTTokenService, Depends(get_token_service)],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = token_service.decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    user = users.get_by_id(payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return AuthenticatedUser(id=user.id, role=user.role)
