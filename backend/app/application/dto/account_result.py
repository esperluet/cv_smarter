from dataclasses import dataclass

from app.domain.models.user import User


@dataclass(frozen=True)
class AccountResult:
    user: User
