from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import ExtractedTriple
from app.schemas.triple import TripleCreateDTO, TripleReadDTO, TripleUpdateDTO
from app.services.source_service import get_source_or_404, mark_project_dirty_if_imported
from app.utils.hash_utils import make_triple_key


def _serialize_triple(triple: ExtractedTriple) -> dict:
    return TripleReadDTO(
        id=triple.id,
        project_id=triple.project_id,
        batch_id=triple.batch_id,
        source_id=triple.source_id,
        subject=triple.subject,
        subject_type=triple.subject_type,
        predicate=triple.predicate,
        object=triple.object,
        object_type=triple.object_type,
        status=triple.status,
        is_manual=bool(triple.is_manual),
        imported=bool(triple.imported),
    ).model_dump()


def _get_active_triple_or_404(db: Session, triple_id: str) -> ExtractedTriple:
    triple = db.get(ExtractedTriple, triple_id)
    if triple is None or triple.status == "deleted":
        raise AppError("TRIPLE_NOT_FOUND", code=4044, status_code=404)
    return triple


def _normalize_required_value(field_name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "TRIPLE_FIELD_REQUIRED",
            code=4010,
            status_code=400,
            data={"field": field_name},
        )
    return normalized


def _mark_source_edited(source) -> None:
    source.is_manual_edited = 1


def list_source_triples(db: Session, source_id: str) -> list[dict]:
    get_source_or_404(db, source_id)
    stmt = (
        select(ExtractedTriple)
        .where(
            ExtractedTriple.source_id == source_id,
            ExtractedTriple.status == "valid",
        )
        .order_by(ExtractedTriple.created_at.asc(), ExtractedTriple.id.asc())
    )
    triples = db.scalars(stmt).all()
    return [_serialize_triple(triple) for triple in triples]


def create_triple(db: Session, source_id: str, payload: TripleCreateDTO) -> dict:
    source = get_source_or_404(db, source_id)
    subject = _normalize_required_value("subject", payload.subject)
    subject_type = _normalize_required_value("subject_type", payload.subject_type)
    predicate = _normalize_required_value("predicate", payload.predicate)
    object_value = _normalize_required_value("object", payload.object)
    object_type = _normalize_required_value("object_type", payload.object_type)

    triple = ExtractedTriple(
        project_id=source.project_id,
        batch_id=source.batch_id,
        source_id=source.id,
        triple_key=make_triple_key(source.project_id, subject, predicate, object_value),
        subject=subject,
        subject_type=subject_type,
        predicate=predicate,
        object=object_value,
        object_type=object_type,
        status="valid",
        is_manual=1,
        imported=0,
    )
    _mark_source_edited(source)
    mark_project_dirty_if_imported(db, source.project_id)
    db.add(triple)
    db.commit()
    db.refresh(triple)
    return _serialize_triple(triple)


def update_triple(db: Session, triple_id: str, payload: TripleUpdateDTO) -> dict:
    triple = _get_active_triple_or_404(db, triple_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return _serialize_triple(triple)

    for field, value in data.items():
        if value is None:
            continue
        setattr(triple, field, _normalize_required_value(field, value))

    triple.triple_key = make_triple_key(
        triple.project_id,
        triple.subject,
        triple.predicate,
        triple.object,
    )
    triple.is_manual = 1
    triple.imported = 0

    source = get_source_or_404(db, triple.source_id)
    _mark_source_edited(source)
    mark_project_dirty_if_imported(db, triple.project_id)
    db.commit()
    db.refresh(triple)
    return _serialize_triple(triple)


def delete_triple(db: Session, triple_id: str) -> None:
    triple = _get_active_triple_or_404(db, triple_id)
    triple.status = "deleted"
    triple.imported = 0

    source = get_source_or_404(db, triple.source_id)
    _mark_source_edited(source)
    mark_project_dirty_if_imported(db, triple.project_id)
    db.commit()
