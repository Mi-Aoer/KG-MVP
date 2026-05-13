from pydantic import BaseModel, Field


class QAAskRequestDTO(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class QAEvidenceDTO(BaseModel):
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    source_text: str


class QAAskResultDTO(BaseModel):
    project_id: str
    question: str
    answer: str
    matched_count: int
    evidence: list[QAEvidenceDTO]
