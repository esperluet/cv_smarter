from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.models.ground_source import GroundSource
from app.infrastructure.persistence.models import GroundSourceORM


class SQLAlchemyGroundSourceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _to_domain(self, row: GroundSourceORM) -> GroundSource:
        return GroundSource(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            original_filename=row.original_filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            storage_path=row.storage_path,
            canonical_text=row.canonical_text,
            content_hash=row.content_hash,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create(
        self,
        *,
        user_id: str,
        name: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        storage_path: str,
        canonical_text: str,
        content_hash: str,
    ) -> GroundSource:
        row = GroundSourceORM(
            user_id=user_id,
            name=name,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            canonical_text=canonical_text,
            content_hash=content_hash,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def list_for_user(self, *, user_id: str) -> list[GroundSource]:
        stmt = (
            select(GroundSourceORM)
            .where(GroundSourceORM.user_id == user_id)
            .order_by(GroundSourceORM.created_at.desc())
        )
        rows = self._db.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def get_for_user(self, *, source_id: str, user_id: str) -> GroundSource | None:
        stmt = select(GroundSourceORM).where(
            GroundSourceORM.id == source_id,
            GroundSourceORM.user_id == user_id,
        )
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def delete_for_user(self, *, source_id: str, user_id: str) -> bool:
        stmt = (
            delete(GroundSourceORM)
            .where(
                GroundSourceORM.id == source_id,
                GroundSourceORM.user_id == user_id,
            )
            .execution_options(synchronize_session=False)
        )
        result = self._db.execute(stmt)
        self._db.commit()
        return bool(result.rowcount)
