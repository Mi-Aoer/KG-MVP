from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.sqlite_models import ModelConfig, Project
from app.schemas.config import ModelConfigCreateDTO, ModelConfigReadDTO, ModelConfigUpdateDTO


def mask_api_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def _serialize_config(config: ModelConfig) -> dict:
    return ModelConfigReadDTO(
        id=config.id,
        config_type=config.config_type,
        name=config.name,
        base_url=config.base_url,
        api_key_masked=mask_api_key(config.api_key),
        model_name=config.model_name,
        timeout_seconds=config.timeout_seconds,
        is_enabled=bool(config.is_enabled),
        created_at=config.created_at,
        updated_at=config.updated_at,
    ).model_dump()


def _get_config_or_404(db: Session, config_id: str) -> ModelConfig:
    config = db.get(ModelConfig, config_id)
    if config is None:
        raise AppError("CONFIG_NOT_FOUND", code=4040, status_code=404)
    return config


def _ensure_config_name_unique(
    db: Session,
    *,
    config_type: str,
    name: str,
    exclude_id: str | None = None,
):
    stmt = select(ModelConfig).where(
        ModelConfig.config_type == config_type,
        ModelConfig.name == name,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if exclude_id is not None and existing.id == exclude_id:
        return
    raise AppError("CONFIG_NAME_ALREADY_EXISTS", code=4090, status_code=409)


def create_config(db: Session, payload: ModelConfigCreateDTO) -> dict:
    _ensure_config_name_unique(db, config_type=payload.config_type, name=payload.name)
    config = ModelConfig(
        config_type=payload.config_type,
        name=payload.name,
        base_url=payload.base_url,
        api_key=payload.api_key,
        model_name=payload.model_name,
        timeout_seconds=payload.timeout_seconds,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return _serialize_config(config)


def list_configs(db: Session) -> list[dict]:
    stmt = select(ModelConfig).order_by(ModelConfig.created_at.desc())
    configs = db.scalars(stmt).all()
    return [_serialize_config(config) for config in configs]


def get_config(db: Session, config_id: str) -> dict:
    return _serialize_config(_get_config_or_404(db, config_id))


def update_config(db: Session, config_id: str, payload: ModelConfigUpdateDTO) -> dict:
    config = _get_config_or_404(db, config_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return _serialize_config(config)

    new_name = data.get("name", config.name)
    _ensure_config_name_unique(
        db,
        config_type=config.config_type,
        name=new_name,
        exclude_id=config.id,
    )

    for field, value in data.items():
        if field == "is_enabled":
            setattr(config, field, int(value))
            continue
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return _serialize_config(config)


def delete_config(db: Session, config_id: str) -> None:
    config = _get_config_or_404(db, config_id)
    referenced_project = db.scalar(
        select(Project).where(
            or_(
                Project.extract_config_id == config_id,
                Project.qa_config_id == config_id,
            )
        )
    )
    if referenced_project is not None:
        raise AppError("CONFIG_IN_USE", code=4091, status_code=409)

    db.delete(config)
    db.commit()
