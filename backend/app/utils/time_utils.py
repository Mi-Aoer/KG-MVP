from datetime import datetime, timezone


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()
