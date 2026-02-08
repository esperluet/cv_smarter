from app.application.dto.account_result import AccountResult
from app.application.errors import UserNotFoundError
from app.domain.repositories.user_repository import UserRepository


class GetMeUseCase:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(self, user_id: str) -> AccountResult:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        return AccountResult(user=user)
