from app.domain.models.ground_source import GroundSource
from app.domain.repositories.ground_source_repository import GroundSourceRepository


class ListGroundSourcesUseCase:
    def __init__(self, *, sources: GroundSourceRepository) -> None:
        self._sources = sources

    def execute(self, *, user_id: str) -> list[GroundSource]:
        return self._sources.list_for_user(user_id=user_id)
