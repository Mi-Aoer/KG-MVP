from typing import Any

from pydantic import BaseModel


class ApiEnvelope(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any | None = None
