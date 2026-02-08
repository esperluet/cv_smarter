from app.application.errors import GroundSourceNotFoundError
from app.domain.repositories.ground_source_repository import GroundSourceRepository


class DeleteGroundSourceUseCase:
    def __init__(self, *, sources: GroundSourceRepository) -> None:
        self._sources = sources

    def execute(self, *, user_id: str, source_id: str) -> None:
        deleted = self._sources.delete_for_user(source_id=source_id, user_id=user_id)
        if not deleted:
            raise GroundSourceNotFoundError("Ground source not found")
