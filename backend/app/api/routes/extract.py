from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.extract import BatchExtractStartDTO
from app.services import extraction_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api", tags=["extract"])


@router.post("/batches/{batch_id}/extract")
def start_extract(
    batch_id: str,
    payload: BatchExtractStartDTO,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    data = extraction_service.start_batch_extract(
        db,
        background_tasks,
        batch_id,
        payload.instruction,
    )
    return ok(data)


@router.get("/batches/{batch_id}/progress")
def get_progress(batch_id: str, db: Session = Depends(get_db)):
    return ok(extraction_service.get_batch_progress(db, batch_id))


@router.post("/batches/{batch_id}/retry-failed")
def retry_failed(
    batch_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    data = extraction_service.retry_failed_sources(db, background_tasks, batch_id)
    return ok(data)


@router.post("/sources/{source_id}/retry")
def retry_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    data = extraction_service.retry_single_source(db, background_tasks, source_id)
    return ok(data)
