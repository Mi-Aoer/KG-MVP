from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import ImportBatch, Project, SourceRecord
from app.schemas.batch import BatchReadDTO, SourceRecordSummaryDTO


def _serialize_batch(batch: ImportBatch) -> dict:
    return BatchReadDTO.model_validate(batch).model_dump()


def _serialize_source(source: SourceRecord) -> dict:
    return SourceRecordSummaryDTO(
        id=source.id,
        batch_id=source.batch_id,
        line_no=source.line_no,
        input_text=source.input_text,
        request_status=source.request_status,
        parse_status=source.parse_status,
        is_manual_edited=bool(source.is_manual_edited),
        error_message=source.error_message,
    ).model_dump()


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", code=4041, status_code=404)
    return project


def _get_batch_or_404(db: Session, batch_id: str) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise AppError("BATCH_NOT_FOUND", code=4042, status_code=404)
    return batch


def _ensure_txt_file(file_name: str) -> None:
    if Path(file_name).suffix.lower() != ".txt":
        raise AppError("INVALID_FILE_TYPE", code=4002, status_code=400)


def upload_txt_batch(db: Session, project_id: str, file_name: str, file_bytes: bytes) -> dict:
    _get_project_or_404(db, project_id)
    _ensure_txt_file(file_name)

    if not file_bytes:
        raise AppError("EMPTY_FILE", code=4003, status_code=400)

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError("INVALID_FILE_ENCODING", code=4005, status_code=400) from exc

    lines = text.splitlines()
    if not lines:
        raise AppError("EMPTY_FILE", code=4003, status_code=400)

    valid_rows: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        if line.strip() == "":
            continue
        valid_rows.append((index, line))

    if not valid_rows:
        raise AppError("NO_VALID_LINES", code=4004, status_code=400)

    batch = ImportBatch(
        project_id=project_id,
        file_name=file_name,
        instruction=None,
        total_lines=len(lines),
        valid_lines=len(valid_rows),
        status="uploaded",
        success_count=0,
        request_failed_count=0,
        parse_failed_count=0,
    )
    db.add(batch)
    db.flush()

    source_records = [
        SourceRecord(
            project_id=project_id,
            batch_id=batch.id,
            line_no=line_no,
            input_text=input_text,
            request_status="pending",
            parse_status="pending",
            is_manual_edited=0,
            retry_count=0,
            error_message=None,
        )
        for line_no, input_text in valid_rows
    ]
    db.add_all(source_records)
    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch)


def list_batches(db: Session, project_id: str) -> list[dict]:
    _get_project_or_404(db, project_id)
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.project_id == project_id)
        .order_by(ImportBatch.created_at.desc())
    )
    batches = db.scalars(stmt).all()
    return [_serialize_batch(batch) for batch in batches]


def get_batch(db: Session, batch_id: str) -> dict:
    return _serialize_batch(_get_batch_or_404(db, batch_id))


def list_batch_sources(db: Session, batch_id: str) -> list[dict]:
    _get_batch_or_404(db, batch_id)
    stmt = (
        select(SourceRecord)
        .where(SourceRecord.batch_id == batch_id)
        .order_by(SourceRecord.line_no.asc())
    )
    sources = db.scalars(stmt).all()
    return [_serialize_source(source) for source in sources]
