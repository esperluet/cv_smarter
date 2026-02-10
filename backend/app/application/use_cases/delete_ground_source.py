from app.application.errors import GroundSourceNotFoundError
from app.domain.repositories.ground_source_repository import GroundSourceRepository
from app.domain.services.file_storage import FileStorage


class DeleteGroundSourceUseCase:
    def __init__(self, *, sources: GroundSourceRepository, storage: FileStorage) -> None:
        self._sources = sources
        self._storage = storage

    def execute(self, *, user_id: str, source_id: str) -> None:
        source = self._sources.get_for_user(source_id=source_id, user_id=user_id)
        if source is None:
            raise GroundSourceNotFoundError("Ground source not found")

        deleted = self._sources.delete_for_user(source_id=source_id, user_id=user_id)
        if not deleted:
            raise GroundSourceNotFoundError("Ground source not found")

        try:
            self._storage.delete(storage_path=source.storage_path)
        except Exception:
            # Business deletion should remain successful even if file cleanup fails.
            pass
