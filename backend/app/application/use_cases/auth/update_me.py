from app.application.dto.account_result import AccountResult
from app.application.errors import UserNotFoundError
from app.domain.repositories.user_repository import UserRepository


class UpdateMeUseCase:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(self, user_id: str, updates: dict[str, str | None]) -> AccountResult:
        user = self._users.update_profile(user_id=user_id, updates=updates)
        if user is None:
            raise UserNotFoundError("User not found")
        return AccountResult(user=user)
