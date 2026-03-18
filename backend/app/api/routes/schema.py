from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schema import EntityTypeCreateDTO, RelationTypeCreateDTO, RenameDTO
from app.services import schema_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api", tags=["schema"])


@router.post("/projects/{project_id}/schema/refresh")
def refresh_schema(project_id: str, db: Session = Depends(get_db)):
    return ok(schema_service.refresh_schema(db, project_id))


@router.get("/projects/{project_id}/schema")
def get_schema(project_id: str, db: Session = Depends(get_db)):
    return ok(schema_service.get_schema(db, project_id))


@router.post("/projects/{project_id}/entity-types")
def create_entity_type(
    project_id: str,
    payload: EntityTypeCreateDTO,
    db: Session = Depends(get_db),
):
    return ok(schema_service.create_entity_type(db, project_id, payload.type_name))


@router.put("/entity-types/{entity_type_id}")
def rename_entity_type(
    entity_type_id: str,
    payload: RenameDTO,
    db: Session = Depends(get_db),
):
    return ok(schema_service.rename_entity_type(db, entity_type_id, payload.new_name))


@router.delete("/entity-types/{entity_type_id}")
def delete_entity_type(entity_type_id: str, db: Session = Depends(get_db)):
    schema_service.delete_entity_type(db, entity_type_id)
    return ok()


@router.post("/projects/{project_id}/relation-types")
def create_relation_type(
    project_id: str,
    payload: RelationTypeCreateDTO,
    db: Session = Depends(get_db),
):
    return ok(schema_service.create_relation_type(db, project_id, payload.relation_name))


@router.put("/relation-types/{relation_type_id}")
def rename_relation_type(
    relation_type_id: str,
    payload: RenameDTO,
    db: Session = Depends(get_db),
):
    return ok(schema_service.rename_relation_type(db, relation_type_id, payload.new_name))


@router.delete("/relation-types/{relation_type_id}")
def delete_relation_type(relation_type_id: str, db: Session = Depends(get_db)):
    schema_service.delete_relation_type(db, relation_type_id)
    return ok()
