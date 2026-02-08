from typing import Protocol

from app.domain.models.user import User


class UserRepository(Protocol):
    def get_by_id(self, user_id: str) -> User | None:
        ...

    def get_by_email(self, email: str) -> User | None:
        ...

    def create(self, email: str, password_hash: str, first_name: str | None, last_name: str | None) -> User:
        ...

    def update_profile(self, user_id: str, updates: dict[str, str | None]) -> User | None:
        ...
