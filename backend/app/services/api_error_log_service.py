import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.sqlite_models import ApiErrorLog


def _serialize_raw_payload(raw_payload: Any | None) -> str | None:
    if raw_payload is None:
        return None
    if isinstance(raw_payload, str):
        return raw_payload
    try:
        return json.dumps(raw_payload, ensure_ascii=False, default=str)
    except TypeError:
        return str(raw_payload)


def log_api_error(
    db: Session,
    *,
    module: str,
    error_code: str,
    error_message: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
    raw_payload: Any | None = None,
) -> None:
    try:
        db.add(
            ApiErrorLog(
                module=module,
                ref_type=ref_type,
                ref_id=ref_id,
                error_code=error_code,
                error_message=error_message,
                raw_payload=_serialize_raw_payload(raw_payload),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
