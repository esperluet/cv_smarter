from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RefreshSession:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
