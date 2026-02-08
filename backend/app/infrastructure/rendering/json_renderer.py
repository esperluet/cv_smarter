import json

from app.domain.models.document_pipeline import CanonicalDocument


class JsonRenderer:
    @property
    def output_format(self) -> str:
        return "json"

    @property
    def media_type(self) -> str:
        return "application/json"

    def render(self, document: CanonicalDocument) -> str:
        return json.dumps(
            {
                "schema_version": document.schema_version,
                "source_media_type": document.source_media_type,
                "text": document.text,
                "metadata": document.metadata,
                "extensions": document.extensions,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
