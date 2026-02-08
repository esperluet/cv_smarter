from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.user import User
from app.domain.repositories.auth_registration_repository import DuplicateEmailError
from app.infrastructure.persistence.models import RefreshSessionORM, UserORM


class SQLAlchemyAuthRegistrationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def register_user_with_refresh_session(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str | None,
        last_name: str | None,
        refresh_token_hash: str,
        refresh_expires_at: datetime,
    ) -> User:
        row = UserORM(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )

        try:
            self._db.add(row)
            self._db.flush()

            refresh_session = RefreshSessionORM(
                user_id=row.id,
                token_hash=refresh_token_hash,
                expires_at=refresh_expires_at,
            )
            self._db.add(refresh_session)
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if _is_email_unique_violation(exc):
                raise DuplicateEmailError("Email is already registered") from exc
            raise

        self._db.refresh(row)
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


def _is_email_unique_violation(exc: IntegrityError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return "unique" in message and "email" in message
