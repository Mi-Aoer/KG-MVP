from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.project import ProjectCreateDTO, ProjectUpdateDTO
from app.services import project_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(payload: ProjectCreateDTO, db: Session = Depends(get_db)):
    return ok(project_service.create_project(db, payload))


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    return ok(project_service.list_projects(db))


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    return ok(project_service.get_project(db, project_id))


@router.put("/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdateDTO,
    db: Session = Depends(get_db),
):
    return ok(project_service.update_project(db, project_id, payload))


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project_service.delete_project(db, project_id)
    return ok()
