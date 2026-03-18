from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import Project, SourceRecord
from app.schemas.source import SourceDetailDTO
from app.utils.time_utils import utcnow_str


def _serialize_source(source: SourceRecord) -> dict:
    return SourceDetailDTO(
        id=source.id,
        batch_id=source.batch_id,
        project_id=source.project_id,
        line_no=source.line_no,
        input_text=source.input_text,
        request_payload=source.request_payload,
        raw_response=source.raw_response,
        cleaned_output_text=source.cleaned_output_text,
        request_status=source.request_status,
        parse_status=source.parse_status,
        is_manual_edited=bool(source.is_manual_edited),
        retry_count=source.retry_count,
        error_message=source.error_message,
    ).model_dump()


def get_source_or_404(db: Session, source_id: str) -> SourceRecord:
    source = db.get(SourceRecord, source_id)
    if source is None:
        raise AppError("SOURCE_NOT_FOUND", code=4043, status_code=404)
    return source


def mark_project_dirty_if_imported(db: Session, project_id: str) -> None:
    project = db.get(Project, project_id)
    if project is None:
        return
    if project.status != "imported":
        return
    project.status = "initialized"
    project.updated_at = utcnow_str()


def get_source_detail(db: Session, source_id: str) -> dict:
    return _serialize_source(get_source_or_404(db, source_id))


def update_raw_response(db: Session, source_id: str, raw_response: str) -> dict:
    source = get_source_or_404(db, source_id)
    if source.raw_response is None:
        raise AppError("RAW_RESPONSE_NOT_FOUND", code=4009, status_code=400)

    source.raw_response = raw_response
    source.cleaned_output_text = None
    source.parse_status = "pending"
    source.is_manual_edited = 1
    source.error_message = None
    mark_project_dirty_if_imported(db, source.project_id)
    db.commit()
    db.refresh(source)
    return _serialize_source(source)
