from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import EntityType, ExtractedTriple, Project, RelationType
from app.schemas.schema import (
    EntityTypeReadDTO,
    ProjectSchemaDTO,
    RelationTypeReadDTO,
    SchemaRefreshResultDTO,
)
from app.services.source_service import mark_project_dirty_if_imported
from app.utils.hash_utils import make_triple_key


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", code=4041, status_code=404)
    return project


def _get_entity_type_or_404(db: Session, entity_type_id: str) -> EntityType:
    entity_type = db.get(EntityType, entity_type_id)
    if entity_type is None:
        raise AppError("ENTITY_TYPE_NOT_FOUND", code=4045, status_code=404)
    return entity_type


def _get_relation_type_or_404(db: Session, relation_type_id: str) -> RelationType:
    relation_type = db.get(RelationType, relation_type_id)
    if relation_type is None:
        raise AppError("RELATION_TYPE_NOT_FOUND", code=4046, status_code=404)
    return relation_type


def _normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise AppError("SCHEMA_NAME_REQUIRED", code=4011, status_code=400)
    return normalized


def _serialize_entity_type(entity_type: EntityType) -> dict:
    return EntityTypeReadDTO(
        id=entity_type.id,
        type_name=entity_type.type_name,
        created_at=entity_type.created_at,
        updated_at=entity_type.updated_at,
    ).model_dump()


def _serialize_relation_type(relation_type: RelationType) -> dict:
    return RelationTypeReadDTO(
        id=relation_type.id,
        relation_name=relation_type.relation_name,
        created_at=relation_type.created_at,
        updated_at=relation_type.updated_at,
    ).model_dump()


def _load_entity_types(db: Session, project_id: str) -> list[EntityType]:
    stmt = (
        select(EntityType)
        .where(EntityType.project_id == project_id)
        .order_by(EntityType.type_name.asc(), EntityType.created_at.asc())
    )
    return db.scalars(stmt).all()


def _load_relation_types(db: Session, project_id: str) -> list[RelationType]:
    stmt = (
        select(RelationType)
        .where(RelationType.project_id == project_id)
        .order_by(RelationType.relation_name.asc(), RelationType.created_at.asc())
    )
    return db.scalars(stmt).all()


def _get_entity_type_names_from_triples(db: Session, project_id: str) -> list[str]:
    subject_types = set(
        db.scalars(
            select(ExtractedTriple.subject_type)
            .where(
                ExtractedTriple.project_id == project_id,
                ExtractedTriple.status == "valid",
            )
            .distinct()
        ).all()
    )
    object_types = set(
        db.scalars(
            select(ExtractedTriple.object_type)
            .where(
                ExtractedTriple.project_id == project_id,
                ExtractedTriple.status == "valid",
            )
            .distinct()
        ).all()
    )
    return sorted({name for name in subject_types | object_types if name})


def _get_relation_type_names_from_triples(db: Session, project_id: str) -> list[str]:
    relation_names = set(
        db.scalars(
            select(ExtractedTriple.predicate)
            .where(
                ExtractedTriple.project_id == project_id,
                ExtractedTriple.status == "valid",
            )
            .distinct()
        ).all()
    )
    return sorted({name for name in relation_names if name})


def _ensure_entity_type_name_unique(
    db: Session,
    project_id: str,
    type_name: str,
    exclude_id: str | None = None,
) -> None:
    existing = db.scalar(
        select(EntityType).where(
            EntityType.project_id == project_id,
            EntityType.type_name == type_name,
        )
    )
    if existing is None:
        return
    if exclude_id is not None and existing.id == exclude_id:
        return
    raise AppError("SCHEMA_NAME_DUPLICATED", code=4096, status_code=409)


def _ensure_relation_type_name_unique(
    db: Session,
    project_id: str,
    relation_name: str,
    exclude_id: str | None = None,
) -> None:
    existing = db.scalar(
        select(RelationType).where(
            RelationType.project_id == project_id,
            RelationType.relation_name == relation_name,
        )
    )
    if existing is None:
        return
    if exclude_id is not None and existing.id == exclude_id:
        return
    raise AppError("SCHEMA_NAME_DUPLICATED", code=4096, status_code=409)


def get_schema(db: Session, project_id: str) -> dict:
    _get_project_or_404(db, project_id)
    entity_types = [_serialize_entity_type(item) for item in _load_entity_types(db, project_id)]
    relation_types = [
        _serialize_relation_type(item) for item in _load_relation_types(db, project_id)
    ]
    return ProjectSchemaDTO(
        project_id=project_id,
        entity_types=entity_types,
        relation_types=relation_types,
    ).model_dump()


def refresh_schema(db: Session, project_id: str) -> dict:
    _get_project_or_404(db, project_id)

    entity_type_names = _get_entity_type_names_from_triples(db, project_id)
    relation_type_names = _get_relation_type_names_from_triples(db, project_id)

    existing_entity_names = {item.type_name for item in _load_entity_types(db, project_id)}
    existing_relation_names = {
        item.relation_name for item in _load_relation_types(db, project_id)
    }

    inserted = False
    for type_name in entity_type_names:
        if type_name in existing_entity_names:
            continue
        db.add(EntityType(project_id=project_id, type_name=type_name))
        inserted = True

    for relation_name in relation_type_names:
        if relation_name in existing_relation_names:
            continue
        db.add(RelationType(project_id=project_id, relation_name=relation_name))
        inserted = True

    if inserted:
        mark_project_dirty_if_imported(db, project_id)

    db.commit()

    return SchemaRefreshResultDTO(
        entity_types=entity_type_names,
        relation_types=relation_type_names,
    ).model_dump()


def create_entity_type(db: Session, project_id: str, type_name: str) -> dict:
    _get_project_or_404(db, project_id)
    normalized_name = _normalize_name(type_name)
    _ensure_entity_type_name_unique(db, project_id, normalized_name)

    entity_type = EntityType(project_id=project_id, type_name=normalized_name)
    mark_project_dirty_if_imported(db, project_id)
    db.add(entity_type)
    db.commit()
    db.refresh(entity_type)
    return _serialize_entity_type(entity_type)


def rename_entity_type(db: Session, entity_type_id: str, new_name: str) -> dict:
    entity_type = _get_entity_type_or_404(db, entity_type_id)
    normalized_name = _normalize_name(new_name)
    _ensure_entity_type_name_unique(
        db,
        entity_type.project_id,
        normalized_name,
        exclude_id=entity_type.id,
    )
    if entity_type.type_name == normalized_name:
        return _serialize_entity_type(entity_type)

    old_name = entity_type.type_name
    triples = db.scalars(
        select(ExtractedTriple).where(
            ExtractedTriple.project_id == entity_type.project_id,
            ExtractedTriple.status == "valid",
            (
                (ExtractedTriple.subject_type == old_name)
                | (ExtractedTriple.object_type == old_name)
            ),
        )
    ).all()

    for triple in triples:
        if triple.subject_type == old_name:
            triple.subject_type = normalized_name
        if triple.object_type == old_name:
            triple.object_type = normalized_name
        triple.imported = 0

    entity_type.type_name = normalized_name
    mark_project_dirty_if_imported(db, entity_type.project_id)
    db.commit()
    db.refresh(entity_type)
    return _serialize_entity_type(entity_type)


def delete_entity_type(db: Session, entity_type_id: str) -> None:
    entity_type = _get_entity_type_or_404(db, entity_type_id)
    reference_count = int(
        db.scalar(
            select(func.count()).select_from(ExtractedTriple).where(
                ExtractedTriple.project_id == entity_type.project_id,
                ExtractedTriple.status == "valid",
                (
                    (ExtractedTriple.subject_type == entity_type.type_name)
                    | (ExtractedTriple.object_type == entity_type.type_name)
                ),
            )
        )
        or 0
    )
    if reference_count > 0:
        raise AppError("ENTITY_TYPE_IN_USE", code=4097, status_code=409)

    mark_project_dirty_if_imported(db, entity_type.project_id)
    db.delete(entity_type)
    db.commit()


def create_relation_type(db: Session, project_id: str, relation_name: str) -> dict:
    _get_project_or_404(db, project_id)
    normalized_name = _normalize_name(relation_name)
    _ensure_relation_type_name_unique(db, project_id, normalized_name)

    relation_type = RelationType(project_id=project_id, relation_name=normalized_name)
    mark_project_dirty_if_imported(db, project_id)
    db.add(relation_type)
    db.commit()
    db.refresh(relation_type)
    return _serialize_relation_type(relation_type)


def rename_relation_type(db: Session, relation_type_id: str, new_name: str) -> dict:
    relation_type = _get_relation_type_or_404(db, relation_type_id)
    normalized_name = _normalize_name(new_name)
    _ensure_relation_type_name_unique(
        db,
        relation_type.project_id,
        normalized_name,
        exclude_id=relation_type.id,
    )
    if relation_type.relation_name == normalized_name:
        return _serialize_relation_type(relation_type)

    old_name = relation_type.relation_name
    triples = db.scalars(
        select(ExtractedTriple).where(
            ExtractedTriple.project_id == relation_type.project_id,
            ExtractedTriple.status == "valid",
            ExtractedTriple.predicate == old_name,
        )
    ).all()

    for triple in triples:
        triple.predicate = normalized_name
        triple.triple_key = make_triple_key(
            triple.project_id,
            triple.subject,
            normalized_name,
            triple.object,
        )
        triple.imported = 0

    relation_type.relation_name = normalized_name
    mark_project_dirty_if_imported(db, relation_type.project_id)
    db.commit()
    db.refresh(relation_type)
    return _serialize_relation_type(relation_type)


def delete_relation_type(db: Session, relation_type_id: str) -> None:
    relation_type = _get_relation_type_or_404(db, relation_type_id)
    reference_count = int(
        db.scalar(
            select(func.count()).select_from(ExtractedTriple).where(
                ExtractedTriple.project_id == relation_type.project_id,
                ExtractedTriple.status == "valid",
                ExtractedTriple.predicate == relation_type.relation_name,
            )
        )
        or 0
    )
    if reference_count > 0:
        raise AppError("RELATION_TYPE_IN_USE", code=4098, status_code=409)

    mark_project_dirty_if_imported(db, relation_type.project_id)
    db.delete(relation_type)
    db.commit()
