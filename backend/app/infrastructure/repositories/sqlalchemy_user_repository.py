from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.user import User
from app.infrastructure.persistence.models import UserORM


class SQLAlchemyUserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _to_domain(self, row: UserORM) -> User:
        return User(
            id=row.id,
            email=row.email,
            password_hash=row.password_hash,
            first_name=row.first_name,
            last_name=row.last_name,
            role=row.role,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def get_by_id(self, user_id: str) -> User | None:
        row = self._db.get(UserORM, user_id)
        if row is None:
            return None
        return self._to_domain(row)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email)
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def create(self, email: str, password_hash: str, first_name: str | None, last_name: str | None) -> User:
        row = UserORM(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def update_profile(self, user_id: str, updates: dict[str, str | None]) -> User | None:
        row = self._db.get(UserORM, user_id)
        if row is None:
            return None

        if "first_name" in updates:
            row.first_name = updates["first_name"]
        if "last_name" in updates:
            row.last_name = updates["last_name"]

        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)
