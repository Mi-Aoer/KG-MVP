from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import ModelConfig, Project
from app.schemas.project import ProjectCreateDTO, ProjectReadDTO, ProjectUpdateDTO


def _serialize_project(project: Project) -> dict:
    return ProjectReadDTO.model_validate(project).model_dump()


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", code=4041, status_code=404)
    return project


def _get_required_config(db: Session, config_id: str, expected_type: str) -> ModelConfig:
    config = db.get(ModelConfig, config_id)
    if config is None:
        raise AppError("CONFIG_NOT_FOUND", code=4040, status_code=404)
    if config.config_type != expected_type:
        raise AppError("CONFIG_TYPE_MISMATCH", code=4001, status_code=400)
    return config


def _ensure_project_name_unique(db: Session, name: str, exclude_id: str | None = None) -> None:
    existing = db.scalar(select(Project).where(Project.name == name))
    if existing is None:
        return
    if exclude_id is not None and existing.id == exclude_id:
        return
    raise AppError("PROJECT_NAME_ALREADY_EXISTS", code=4092, status_code=409)


def create_project(db: Session, payload: ProjectCreateDTO) -> dict:
    _ensure_project_name_unique(db, payload.name)
    _get_required_config(db, payload.extract_config_id, "extract")
    _get_required_config(db, payload.qa_config_id, "qa")

    project = Project(
        name=payload.name,
        description=payload.description,
        extract_config_id=payload.extract_config_id,
        qa_config_id=payload.qa_config_id,
        status="ready",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _serialize_project(project)


def list_projects(db: Session) -> list[dict]:
    stmt = select(Project).order_by(Project.created_at.desc())
    projects = db.scalars(stmt).all()
    return [_serialize_project(project) for project in projects]


def get_project(db: Session, project_id: str) -> dict:
    return _serialize_project(_get_project_or_404(db, project_id))


def update_project(db: Session, project_id: str, payload: ProjectUpdateDTO) -> dict:
    project = _get_project_or_404(db, project_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return _serialize_project(project)

    if "name" in data:
        _ensure_project_name_unique(db, data["name"], exclude_id=project.id)

    if "extract_config_id" in data:
        _get_required_config(db, data["extract_config_id"], "extract")

    if "qa_config_id" in data:
        _get_required_config(db, data["qa_config_id"], "qa")

    for field, value in data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return _serialize_project(project)


def delete_project(db: Session, project_id: str) -> None:
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
