import json

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models.sqlite_models import ImportBatch, ModelConfig, Project, SourceRecord
from app.schemas.extract import BatchProgressDTO
from app.services.llm_client import LLMClientError, get_llm_client
from app.utils.time_utils import utcnow_str


def _get_batch_or_404(db: Session, batch_id: str) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise AppError("BATCH_NOT_FOUND", code=4042, status_code=404)
    return batch


def _get_source_or_404(db: Session, source_id: str) -> SourceRecord:
    source = db.get(SourceRecord, source_id)
    if source is None:
        raise AppError("SOURCE_NOT_FOUND", code=4043, status_code=404)
    return source


def _get_extract_config(db: Session, batch: ImportBatch) -> tuple[Project, ModelConfig]:
    project = db.get(Project, batch.project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", code=4041, status_code=404)

    config = db.get(ModelConfig, project.extract_config_id)
    if config is None:
        raise AppError("CONFIG_NOT_FOUND", code=4040, status_code=404)
    if config.config_type != "extract":
        raise AppError("CONFIG_TYPE_MISMATCH", code=4001, status_code=400)
    if not bool(config.is_enabled):
        raise AppError("CONFIG_DISABLED", code=4006, status_code=400)
    return project, config


def _get_batch_counters(db: Session, batch_id: str, total: int) -> dict:
    stmt = select(SourceRecord.request_status, SourceRecord.parse_status).where(
        SourceRecord.batch_id == batch_id
    )
    rows = db.execute(stmt).all()
    processed = sum(1 for request_status, _ in rows if request_status in {"success", "failed"})
    parse_failed_count = sum(1 for _, parse_status in rows if parse_status == "failed")
    request_failed_count = sum(1 for request_status, _ in rows if request_status == "failed")
    success_count = sum(
        1
        for request_status, parse_status in rows
        if request_status == "success" and parse_status != "failed"
    )

    if processed < total:
        status = "extracting"
    elif success_count == total and total > 0:
        status = "success"
    elif success_count > 0:
        status = "partial_success"
    else:
        status = "failed"

    return {
        "status": status,
        "processed": processed,
        "success_count": success_count,
        "request_failed_count": request_failed_count,
        "parse_failed_count": parse_failed_count,
        "total": total,
    }


def refresh_batch_status(db: Session, batch_id: str) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    counters = _get_batch_counters(db, batch_id, batch.valid_lines)
    batch.status = counters["status"]
    batch.success_count = counters["success_count"]
    batch.request_failed_count = counters["request_failed_count"]
    batch.parse_failed_count = counters["parse_failed_count"]
    if counters["status"] == "extracting":
        batch.finished_at = None
    else:
        batch.finished_at = utcnow_str()
    db.commit()
    db.refresh(batch)
    return counters


def _mark_source_for_retry(source: SourceRecord) -> None:
    source.request_status = "pending"
    source.parse_status = "pending"
    source.request_payload = None
    source.raw_response = None
    source.error_message = None


def _select_batch_sources_for_processing(db: Session, batch_id: str) -> list[SourceRecord]:
    stmt = (
        select(SourceRecord)
        .where(SourceRecord.batch_id == batch_id)
        .where(
            (SourceRecord.request_status.in_(["pending", "failed"]))
            | (SourceRecord.parse_status == "failed")
        )
        .order_by(SourceRecord.line_no.asc())
    )
    return db.scalars(stmt).all()


def _serialize_start_response(batch: ImportBatch, queued: int | None = None) -> dict:
    data = {"batch_id": batch.id, "status": batch.status}
    if queued is not None:
        data["queued"] = queued
    return data


def start_batch_extract(
    db: Session,
    background_tasks: BackgroundTasks,
    batch_id: str,
    instruction: str,
) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    if batch.status == "extracting":
        raise AppError("BATCH_ALREADY_EXTRACTING", code=4093, status_code=409)

    _get_extract_config(db, batch)

    batch.instruction = instruction
    batch.status = "extracting"
    batch.started_at = utcnow_str()
    batch.finished_at = None
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(run_batch_extract_task, batch.id)
    return _serialize_start_response(batch)


def get_batch_progress(db: Session, batch_id: str) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    counters = _get_batch_counters(db, batch_id, batch.valid_lines)
    return BatchProgressDTO(
        batch_id=batch.id,
        status=counters["status"],
        total=counters["total"],
        processed=counters["processed"],
        success_count=counters["success_count"],
        request_failed_count=counters["request_failed_count"],
        parse_failed_count=counters["parse_failed_count"],
    ).model_dump()


def retry_failed_sources(
    db: Session,
    background_tasks: BackgroundTasks,
    batch_id: str,
) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    if batch.status == "extracting":
        raise AppError("BATCH_ALREADY_EXTRACTING", code=4093, status_code=409)
    if not batch.instruction:
        raise AppError("BATCH_INSTRUCTION_REQUIRED", code=4007, status_code=400)

    stmt = select(SourceRecord).where(
        SourceRecord.batch_id == batch_id,
        (SourceRecord.request_status == "failed") | (SourceRecord.parse_status == "failed"),
    )
    sources = db.scalars(stmt).all()
    if not sources:
        return _serialize_start_response(batch, queued=0)

    for source in sources:
        _mark_source_for_retry(source)

    batch.status = "extracting"
    batch.finished_at = None
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(run_batch_extract_task, batch.id)
    return _serialize_start_response(batch, queued=len(sources))


def retry_single_source(
    db: Session,
    background_tasks: BackgroundTasks,
    source_id: str,
) -> dict:
    source = _get_source_or_404(db, source_id)
    batch = _get_batch_or_404(db, source.batch_id)
    if batch.status == "extracting":
        raise AppError("BATCH_ALREADY_EXTRACTING", code=4093, status_code=409)
    if not batch.instruction:
        raise AppError("BATCH_INSTRUCTION_REQUIRED", code=4007, status_code=400)
    if source.request_status != "failed" and source.parse_status != "failed":
        raise AppError("SOURCE_NOT_RETRYABLE", code=4008, status_code=400)

    _mark_source_for_retry(source)
    batch.status = "extracting"
    batch.finished_at = None
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(run_single_source_extract_task, source.id)
    return _serialize_start_response(batch, queued=1)


def _process_source(db: Session, batch: ImportBatch, config: ModelConfig, source: SourceRecord) -> None:
    source.request_status = "running"
    source.parse_status = "pending"
    source.error_message = None
    db.commit()
    db.refresh(source)

    request_payload = {
        "model": config.model_name,
        "instruction": batch.instruction or "",
        "input": source.input_text,
    }
    source.request_payload = json.dumps(request_payload, ensure_ascii=False)
    db.commit()

    client = get_llm_client(config.base_url)
    try:
        raw_response = client.call(
            base_url=config.base_url,
            api_key=config.api_key,
            model_name=config.model_name,
            instruction=batch.instruction or "",
            input_text=source.input_text,
            timeout_seconds=config.timeout_seconds,
        )
    except LLMClientError as exc:
        source.request_status = "failed"
        source.error_message = exc.message
        source.retry_count += 1
        db.commit()
        db.refresh(source)
        refresh_batch_status(db, batch.id)
        return
    except Exception as exc:  # pragma: no cover - defensive fallback
        source.request_status = "failed"
        source.error_message = f"UNEXPECTED_ERROR | exception={type(exc).__name__} | detail={exc}"
        source.retry_count += 1
        db.commit()
        db.refresh(source)
        refresh_batch_status(db, batch.id)
        return

    source.raw_response = raw_response
    source.request_status = "success"
    source.parse_status = "pending"
    source.error_message = None
    db.commit()
    db.refresh(source)
    refresh_batch_status(db, batch.id)


def run_batch_extract_task(batch_id: str) -> None:
    db = SessionLocal()
    try:
        batch = db.get(ImportBatch, batch_id)
        if batch is None:
            return
        try:
            _, config = _get_extract_config(db, batch)
        except AppError:
            batch.status = "failed"
            batch.finished_at = utcnow_str()
            db.commit()
            return
        sources = _select_batch_sources_for_processing(db, batch_id)
        for source in sources:
            _process_source(db, batch, config, source)
        refresh_batch_status(db, batch_id)
    except Exception:  # pragma: no cover - defensive fallback
        batch = db.get(ImportBatch, batch_id)
        if batch is not None:
            batch.status = "failed"
            batch.finished_at = utcnow_str()
            db.commit()
    finally:
        db.close()


def run_single_source_extract_task(source_id: str) -> None:
    db = SessionLocal()
    try:
        source = db.get(SourceRecord, source_id)
        if source is None:
            return
        batch = db.get(ImportBatch, source.batch_id)
        if batch is None:
            return
        try:
            _, config = _get_extract_config(db, batch)
        except AppError:
            batch.status = "failed"
            batch.finished_at = utcnow_str()
            source.request_status = "failed"
            source.error_message = "CONFIG_NOT_AVAILABLE"
            db.commit()
            return
        _process_source(db, batch, config, source)
        refresh_batch_status(db, batch.id)
    except Exception:  # pragma: no cover - defensive fallback
        source = db.get(SourceRecord, source_id)
        if source is not None:
            source.request_status = "failed"
            source.error_message = "UNEXPECTED_BACKGROUND_ERROR"
            db.commit()
            batch = db.get(ImportBatch, source.batch_id)
            if batch is not None:
                batch.status = "failed"
                batch.finished_at = utcnow_str()
                db.commit()
    finally:
        db.close()
