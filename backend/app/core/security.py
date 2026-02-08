from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def expires_at_from_days(days: int) -> datetime:
    return utc_now() + timedelta(days=days)
