from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies.auth import AuthenticatedUser, get_current_user, get_user_repository
from app.api.v1.schemas.account import AccountResponse, UpdateAccountRequest
from app.api.v1.schemas.auth import UserResponse
from app.application.errors import UserNotFoundError
from app.application.use_cases.auth.get_me import GetMeUseCase
from app.application.use_cases.auth.update_me import UpdateMeUseCase
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me", response_model=AccountResponse)
def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    users: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> AccountResponse:
    use_case = GetMeUseCase(users=users)

    try:
        result = use_case.execute(user_id=current_user.id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AccountResponse(user=UserResponse.model_validate(result.user))


@router.patch("/me", response_model=AccountResponse)
def update_me(
    payload: UpdateAccountRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    users: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> AccountResponse:
    use_case = UpdateMeUseCase(users=users)

    try:
        updates = payload.model_dump(exclude_unset=True)
        result = use_case.execute(user_id=current_user.id, updates=updates)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AccountResponse(user=UserResponse.model_validate(result.user))
