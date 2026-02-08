from typing import Protocol

from app.domain.models.ground_source import GroundSource


class GroundSourceRepository(Protocol):
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
        ...

    def list_for_user(self, *, user_id: str) -> list[GroundSource]:
        ...

    def get_for_user(self, *, source_id: str, user_id: str) -> GroundSource | None:
        ...

    def delete_for_user(self, *, source_id: str, user_id: str) -> bool:
        ...
