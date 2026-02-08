from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredFile:
    original_name: str
    content_type: str
    size_bytes: int
    storage_path: Path
