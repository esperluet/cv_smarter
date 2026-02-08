from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    first_name: str | None
    last_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
