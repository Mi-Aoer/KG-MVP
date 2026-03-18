from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import graph_service
from app.utils.response_utils import ok


router = APIRouter(prefix="/api", tags=["graph"])


@router.post("/projects/{project_id}/graph/init")
def init_graph(project_id: str, db: Session = Depends(get_db)):
    return ok(graph_service.init_graph(db, project_id))


@router.post("/projects/{project_id}/graph/import")
def import_graph(project_id: str, db: Session = Depends(get_db)):
    return ok(graph_service.import_graph(db, project_id, mode="incremental"))


@router.post("/projects/{project_id}/graph/rebuild")
def rebuild_graph(project_id: str, db: Session = Depends(get_db)):
    return ok(graph_service.import_graph(db, project_id, mode="rebuild"))


@router.get("/projects/{project_id}/graph/import-logs")
def list_import_logs(project_id: str, db: Session = Depends(get_db)):
    return ok(graph_service.list_import_logs(db, project_id))
