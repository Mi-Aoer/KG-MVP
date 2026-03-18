from pydantic import BaseModel, ConfigDict, Field


class ProjectCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    extract_config_id: str


class ProjectUpdateDTO(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    extract_config_id: str | None = None


class ProjectReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    extract_config_id: str
    status: str
    created_at: str
    updated_at: str
    last_import_at: str | None = None
