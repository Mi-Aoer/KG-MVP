from pydantic import BaseModel, ConfigDict, Field


class RawResponseUpdateDTO(BaseModel):
    raw_response: str = Field(min_length=1)


class SourceDetailDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    project_id: str
    line_no: int
    input_text: str
    request_payload: str | None
    raw_response: str | None
    cleaned_output_text: str | None
    request_status: str
    parse_status: str
    is_manual_edited: bool
    retry_count: int
    error_message: str | None
