from pydantic import BaseModel, Field

from app.api.v1.schemas.auth import UserResponse


class UpdateAccountRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)


class AccountResponse(BaseModel):
    user: UserResponse
