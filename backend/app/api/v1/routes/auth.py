from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies.auth import (
    get_refresh_session_use_case,
    get_sign_in_use_case,
    get_sign_out_use_case,
    get_sign_up_use_case,
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
    use_case: Annotated[SignUpUseCase, Depends(get_sign_up_use_case)],
) -> AuthResponse:
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
    use_case: Annotated[SignInUseCase, Depends(get_sign_in_use_case)],
) -> AuthResponse:
    try:
        result = use_case.execute(email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _to_auth_response(result)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    payload: RefreshTokenRequest,
    use_case: Annotated[RefreshSessionUseCase, Depends(get_refresh_session_use_case)],
) -> AuthResponse:
    try:
        result = use_case.execute(refresh_token=payload.refresh_token)
    except (InvalidRefreshTokenError, UserNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _to_auth_response(result)


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    payload: SignOutRequest,
    use_case: Annotated[SignOutUseCase, Depends(get_sign_out_use_case)],
) -> None:
    use_case.execute(refresh_token=payload.refresh_token)
