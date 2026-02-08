from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GroundSource:
    id: str
    user_id: str
    name: str
    original_filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    canonical_text: str
    content_hash: str
    created_at: datetime
    updated_at: datetime
