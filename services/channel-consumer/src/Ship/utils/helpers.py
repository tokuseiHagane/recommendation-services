import json
from datetime import datetime, timezone


def json_dumps(data) -> str:
    """Serialize data to a pretty JSON string (UTF-8 safe)."""
    return json.dumps(data, ensure_ascii=False, default=str)


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)
