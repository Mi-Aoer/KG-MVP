from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import ExtractedTriple, SourceRecord
from app.services.source_service import get_source_or_404, mark_project_dirty_if_imported
from app.utils.hash_utils import make_triple_key
from app.utils.json_cleaner import ParseError, extract_output_string, parse_cleaned_output_text


def _count_active_triples(db: Session, source_id: str) -> int:
    stmt = select(func.count()).select_from(ExtractedTriple).where(
        ExtractedTriple.source_id == source_id,
        ExtractedTriple.status == "valid",
    )
    return int(db.scalar(stmt) or 0)


def _delete_auto_triples(db: Session, source_id: str) -> None:
    stmt = select(ExtractedTriple).where(
        ExtractedTriple.source_id == source_id,
        ExtractedTriple.is_manual == 0,
    )
    for triple in db.scalars(stmt).all():
        db.delete(triple)
    db.flush()


def _insert_auto_triples(db: Session, source: SourceRecord, triples: list[dict]) -> None:
    if not triples:
        return

    db.add_all(
        [
            ExtractedTriple(
                project_id=source.project_id,
                batch_id=source.batch_id,
                source_id=source.id,
                triple_key=make_triple_key(
                    source.project_id,
                    triple["subject"],
                    triple["predicate"],
                    triple["object"],
                ),
                subject=triple["subject"],
                subject_type=triple["subject_type"],
                predicate=triple["predicate"],
                object=triple["object"],
                object_type=triple["object_type"],
                status="valid",
                is_manual=0,
                imported=0,
            )
            for triple in triples
        ]
    )


def _serialize_reparse_result(source: SourceRecord, triple_count: int) -> dict:
    return {
        "source_id": source.id,
        "parse_status": source.parse_status,
        "triple_count": triple_count,
        "error_message": source.error_message,
    }


def _apply_reparse(db: Session, source: SourceRecord, *, mark_dirty: bool) -> dict:
    _delete_auto_triples(db, source.id)

    cleaned_output_text: str | None = None
    try:
        cleaned_output_text = extract_output_string(source.raw_response or "")
        triples = parse_cleaned_output_text(cleaned_output_text)
    except ParseError as exc:
        source.cleaned_output_text = cleaned_output_text
        source.parse_status = "failed"
        source.error_message = str(exc)
        db.commit()
        db.refresh(source)
        return _serialize_reparse_result(source, _count_active_triples(db, source.id))

    _insert_auto_triples(db, source, triples)
    source.cleaned_output_text = cleaned_output_text
    source.parse_status = "success"
    source.error_message = None
    if mark_dirty:
        source.is_manual_edited = 1
        mark_project_dirty_if_imported(db, source.project_id)
    db.commit()
    db.refresh(source)
    return _serialize_reparse_result(source, _count_active_triples(db, source.id))


def parse_source_after_extract(db: Session, source_id: str) -> dict:
    source = get_source_or_404(db, source_id)
    if source.raw_response is None:
        raise AppError("RAW_RESPONSE_NOT_FOUND", code=4009, status_code=400)
    return _apply_reparse(db, source, mark_dirty=False)


def reparse_source(db: Session, source_id: str) -> dict:
    source = get_source_or_404(db, source_id)
    if source.raw_response is None:
        raise AppError("RAW_RESPONSE_NOT_FOUND", code=4009, status_code=400)
    return _apply_reparse(db, source, mark_dirty=True)
