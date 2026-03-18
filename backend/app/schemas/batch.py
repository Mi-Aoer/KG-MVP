from pydantic import BaseModel, ConfigDict


class BatchReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_name: str
    instruction: str | None
    total_lines: int
    valid_lines: int
    status: str
    success_count: int
    request_failed_count: int
    parse_failed_count: int
    created_at: str
    updated_at: str


class SourceRecordSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    line_no: int
    input_text: str
    request_status: str
    parse_status: str
    is_manual_edited: bool
    error_message: str | None
