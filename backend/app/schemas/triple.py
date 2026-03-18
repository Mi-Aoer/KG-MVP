from pydantic import BaseModel, ConfigDict, Field


class TripleCreateDTO(BaseModel):
    subject: str = Field(min_length=1)
    subject_type: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    object_type: str = Field(min_length=1)


class TripleUpdateDTO(BaseModel):
    subject: str | None = Field(default=None, min_length=1)
    subject_type: str | None = Field(default=None, min_length=1)
    predicate: str | None = Field(default=None, min_length=1)
    object: str | None = Field(default=None, min_length=1)
    object_type: str | None = Field(default=None, min_length=1)


class TripleReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    batch_id: str
    source_id: str
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    status: str
    is_manual: bool
    imported: bool
