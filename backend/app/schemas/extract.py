from pydantic import BaseModel, Field


class BatchExtractStartDTO(BaseModel):
    instruction: str = Field(min_length=1)


class BatchProgressDTO(BaseModel):
    batch_id: str
    status: str
    total: int
    processed: int
    success_count: int
    request_failed_count: int
    parse_failed_count: int
