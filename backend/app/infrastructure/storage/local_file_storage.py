import re
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.domain.models.stored_file import StoredFile
from app.domain.services.file_storage import FileTooLargeError


class LocalFileStorage:
    def __init__(self, upload_dir: str, chunk_size: int = 1024 * 1024) -> None:
        self._upload_dir = Path(upload_dir).resolve()
        self._chunk_size = chunk_size
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def save_from_stream(
        self,
        *,
        stream: BinaryIO,
        original_name: str,
        content_type: str,
        max_size_bytes: int,
    ) -> StoredFile:
        safe_name = self._sanitize_filename(original_name)
        stored_name = f"{uuid4().hex}_{safe_name}"
        target_path = self._upload_dir / stored_name

        total_size = 0
        try:
            with target_path.open("wb") as target:
                while True:
                    chunk = stream.read(self._chunk_size)
                    if not chunk:
                        break

                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        raise FileTooLargeError("File is too large")

                    target.write(chunk)
        except FileTooLargeError:
            target_path.unlink(missing_ok=True)
            raise

        return StoredFile(
            original_name=safe_name,
            content_type=content_type,
            size_bytes=total_size,
            storage_path=target_path,
        )

    def _sanitize_filename(self, filename: str) -> str:
        candidate = Path(filename).name.strip()
        if not candidate:
            return "uploaded_file"

        sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", candidate)
        return sanitized or "uploaded_file"

    def delete(self, *, storage_path: str) -> None:
        try:
            resolved_path = Path(storage_path).resolve()
        except OSError:
            return

        if self._upload_dir != resolved_path and self._upload_dir not in resolved_path.parents:
            return

        resolved_path.unlink(missing_ok=True)
