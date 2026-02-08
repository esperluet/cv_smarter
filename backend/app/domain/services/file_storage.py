from typing import BinaryIO, Protocol

from app.domain.models.stored_file import StoredFile


class FileStorageError(Exception):
    pass


class FileTooLargeError(FileStorageError):
    pass


class FileStorage(Protocol):
    def save_from_stream(
        self,
        *,
        stream: BinaryIO,
        original_name: str,
        content_type: str,
        max_size_bytes: int,
    ) -> StoredFile:
        ...

    def delete(self, *, storage_path: str) -> None:
        ...
