from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import batch_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api", tags=["batches"])


@router.post("/projects/{project_id}/batches/upload")
async def upload_batch(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    data = batch_service.upload_txt_batch(
        db=db,
        project_id=project_id,
        file_name=file.filename or "unknown.txt",
        file_bytes=content,
    )
    return ok(data)


@router.get("/projects/{project_id}/batches")
def list_batches(project_id: str, db: Session = Depends(get_db)):
    return ok(batch_service.list_batches(db, project_id))


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    return ok(batch_service.get_batch(db, batch_id))


@router.get("/batches/{batch_id}/sources")
def list_batch_sources(batch_id: str, db: Session = Depends(get_db)):
    return ok(batch_service.list_batch_sources(db, batch_id))
