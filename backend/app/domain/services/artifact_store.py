from typing import Protocol

from app.domain.models.document_pipeline import InputDocument, RenderedArtifact


class ArtifactStore(Protocol):
    def save_artifact(
        self,
        *,
        source_document: InputDocument,
        output_format: str,
        media_type: str,
        content: str,
    ) -> RenderedArtifact:
        ...
