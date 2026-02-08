import re
from pathlib import Path
from uuid import uuid4

from app.domain.models.document_pipeline import InputDocument, RenderedArtifact


class LocalArtifactStore:
    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save_artifact(
        self,
        *,
        source_document: InputDocument,
        output_format: str,
        media_type: str,
        content: str,
    ) -> RenderedArtifact:
        source_stem = self._sanitize(source_document.source_path.stem)
        filename = f"{source_stem}_{uuid4().hex}.{self._extension_for(output_format)}"
        artifact_path = self._base_dir / filename
        artifact_path.write_text(content, encoding="utf-8")

        return RenderedArtifact(
            format=output_format,
            media_type=media_type,
            storage_path=str(artifact_path),
        )

    def _extension_for(self, output_format: str) -> str:
        if output_format == "markdown":
            return "md"
        if output_format == "json":
            return "json"
        return output_format

    def _sanitize(self, value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", value)
        return sanitized or "document"
