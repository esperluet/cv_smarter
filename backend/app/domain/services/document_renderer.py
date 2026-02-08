from typing import Protocol

from app.domain.models.document_pipeline import CanonicalDocument


class DocumentRenderer(Protocol):
    @property
    def output_format(self) -> str:
        ...

    @property
    def media_type(self) -> str:
        ...

    def render(self, document: CanonicalDocument) -> str:
        ...
