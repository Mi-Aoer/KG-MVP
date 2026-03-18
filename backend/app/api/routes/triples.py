from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.triple import TripleCreateDTO, TripleUpdateDTO
from app.services import triple_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api", tags=["triples"])


@router.get("/sources/{source_id}/triples")
def list_source_triples(source_id: str, db: Session = Depends(get_db)):
    return ok(triple_service.list_source_triples(db, source_id))


@router.post("/sources/{source_id}/triples")
def create_source_triple(
    source_id: str,
    payload: TripleCreateDTO,
    db: Session = Depends(get_db),
):
    return ok(triple_service.create_triple(db, source_id, payload))


@router.put("/triples/{triple_id}")
def update_triple(
    triple_id: str,
    payload: TripleUpdateDTO,
    db: Session = Depends(get_db),
):
    return ok(triple_service.update_triple(db, triple_id, payload))


@router.delete("/triples/{triple_id}")
def delete_triple(triple_id: str, db: Session = Depends(get_db)):
    triple_service.delete_triple(db, triple_id)
    return ok()
