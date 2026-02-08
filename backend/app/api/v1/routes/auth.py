from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies.auth import (
    get_auth_registration_repository,
    get_mailer,
    get_password_hasher,
    get_refresh_session_repository,
    get_token_service,
    get_user_repository,
)
from app.api.v1.schemas.auth import (
    AuthResponse,
    RefreshTokenRequest,
    SignInRequest,
    SignOutRequest,
    SignUpRequest,
    UserResponse,
)
from app.application.dto.auth_result import AuthResult
from app.application.errors import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserNotFoundError,
)
from app.application.use_cases.auth.refresh_session import RefreshSessionUseCase
from app.application.use_cases.auth.sign_in import SignInUseCase
from app.application.use_cases.auth.sign_out import SignOutUseCase
from app.application.use_cases.auth.sign_up import SignUpUseCase
from app.infrastructure.mailer.smtp_mailer import SMTPMailer
from app.infrastructure.repositories.sqlalchemy_auth_registration_repository import SQLAlchemyAuthRegistrationRepository
from app.infrastructure.repositories.sqlalchemy_refresh_session_repository import SQLAlchemyRefreshSessionRepository
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.domain.services.password_hasher import PasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        user=UserResponse.model_validate(result.user),
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in_seconds=result.expires_in_seconds,
    )


@router.post("/sign-up", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def sign_up(
    payload: SignUpRequest,
    registration: Annotated[SQLAlchemyAuthRegistrationRepository, Depends(get_auth_registration_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[JWTTokenService, Depends(get_token_service)],
    mailer: Annotated[SMTPMailer, Depends(get_mailer)],
) -> AuthResponse:
    use_case = SignUpUseCase(
        registration=registration,
        password_hasher=password_hasher,
        token_service=token_service,
        mailer=mailer,
    )

    try:
        result = use_case.execute(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return _to_auth_response(result)


@router.post("/sign-in", response_model=AuthResponse)
def sign_in(
    payload: SignInRequest,
    users: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    sessions: Annotated[SQLAlchemyRefreshSessionRepository, Depends(get_refresh_session_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[JWTTokenService, Depends(get_token_service)],
) -> AuthResponse:
    use_case = SignInUseCase(
        users=users,
        sessions=sessions,
        password_hasher=password_hasher,
        token_service=token_service,
    )

    try:
        result = use_case.execute(email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _to_auth_response(result)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    payload: RefreshTokenRequest,
    users: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    sessions: Annotated[SQLAlchemyRefreshSessionRepository, Depends(get_refresh_session_repository)],
    token_service: Annotated[JWTTokenService, Depends(get_token_service)],
) -> AuthResponse:
    use_case = RefreshSessionUseCase(users=users, sessions=sessions, token_service=token_service)

    try:
        result = use_case.execute(refresh_token=payload.refresh_token)
    except (InvalidRefreshTokenError, UserNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _to_auth_response(result)


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    payload: SignOutRequest,
    sessions: Annotated[SQLAlchemyRefreshSessionRepository, Depends(get_refresh_session_repository)],
    token_service: Annotated[JWTTokenService, Depends(get_token_service)],
) -> None:
    use_case = SignOutUseCase(sessions=sessions, token_service=token_service)
    use_case.execute(refresh_token=payload.refresh_token)
