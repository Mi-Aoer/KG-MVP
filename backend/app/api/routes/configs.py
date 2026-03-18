from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.config import ModelConfigCreateDTO, ModelConfigUpdateDTO
from app.services import config_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.post("")
def create_config(payload: ModelConfigCreateDTO, db: Session = Depends(get_db)):
    return ok(config_service.create_config(db, payload))


@router.get("")
def list_configs(db: Session = Depends(get_db)):
    return ok(config_service.list_configs(db))


@router.get("/{config_id}")
def get_config(config_id: str, db: Session = Depends(get_db)):
    return ok(config_service.get_config(db, config_id))


@router.put("/{config_id}")
def update_config(
    config_id: str,
    payload: ModelConfigUpdateDTO,
    db: Session = Depends(get_db),
):
    return ok(config_service.update_config(db, config_id, payload))


@router.delete("/{config_id}")
def delete_config(config_id: str, db: Session = Depends(get_db)):
    config_service.delete_config(db, config_id)
    return ok()
