from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.qa import QAAskRequestDTO
from app.services import qa_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api/projects", tags=["qa"])


@router.post("/{project_id}/qa/ask")
def ask_question(project_id: str, payload: QAAskRequestDTO, db: Session = Depends(get_db)):
    return ok(qa_service.ask_question(db, project_id, payload))
