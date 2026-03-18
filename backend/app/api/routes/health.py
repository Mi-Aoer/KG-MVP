from fastapi import APIRouter

from app.schemas.common import ApiEnvelope
from app.utils.response_utils import ok


router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiEnvelope)
def health():
    return ok({"status": "ok"})
