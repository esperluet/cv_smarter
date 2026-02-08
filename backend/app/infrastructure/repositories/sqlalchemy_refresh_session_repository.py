from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.refresh_session import RefreshSession
from app.infrastructure.persistence.models import RefreshSessionORM


class SQLAlchemyRefreshSessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _to_domain(self, row: RefreshSessionORM) -> RefreshSession:
        return RefreshSession(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
        )

    def create(self, user_id: str, token_hash: str, expires_at: datetime) -> RefreshSession:
        row = RefreshSessionORM(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def get_valid(self, token_hash: str, now: datetime) -> RefreshSession | None:
        stmt = select(RefreshSessionORM).where(
            RefreshSessionORM.token_hash == token_hash,
            RefreshSessionORM.revoked_at.is_(None),
            RefreshSessionORM.expires_at > now,
        )
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def revoke(self, token_hash: str, revoked_at: datetime) -> bool:
        stmt = select(RefreshSessionORM).where(
            RefreshSessionORM.token_hash == token_hash,
            RefreshSessionORM.revoked_at.is_(None),
        )
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return False

        row.revoked_at = revoked_at
        self._db.commit()
        return True

    def rotate(self, old_token_hash: str, new_token_hash: str, expires_at: datetime, now: datetime) -> RefreshSession | None:
        stmt = select(RefreshSessionORM).where(
            RefreshSessionORM.token_hash == old_token_hash,
            RefreshSessionORM.revoked_at.is_(None),
            RefreshSessionORM.expires_at > now,
        )
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return None

        row.revoked_at = now
        new_row = RefreshSessionORM(user_id=row.user_id, token_hash=new_token_hash, expires_at=expires_at)
        self._db.add(new_row)
        self._db.commit()
        self._db.refresh(new_row)
        return self._to_domain(new_row)
