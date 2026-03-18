from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.source import RawResponseUpdateDTO
from app.services import parse_service, source_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/sources/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    return ok(source_service.get_source_detail(db, source_id))


@router.put("/sources/{source_id}/raw-response")
def update_raw_response(
    source_id: str,
    payload: RawResponseUpdateDTO,
    db: Session = Depends(get_db),
):
    return ok(source_service.update_raw_response(db, source_id, payload.raw_response))


@router.post("/sources/{source_id}/reparse")
def reparse_source(source_id: str, db: Session = Depends(get_db)):
    return ok(parse_service.reparse_source(db, source_id))
