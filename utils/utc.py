from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC as naive datetime (matches DB DateTime storage convention)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
