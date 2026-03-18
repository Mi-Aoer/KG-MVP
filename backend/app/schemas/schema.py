from pydantic import BaseModel, Field


class EntityTypeReadDTO(BaseModel):
    id: str
    type_name: str
    created_at: str
    updated_at: str


class RelationTypeReadDTO(BaseModel):
    id: str
    relation_name: str
    created_at: str
    updated_at: str


class ProjectSchemaDTO(BaseModel):
    project_id: str
    entity_types: list[EntityTypeReadDTO]
    relation_types: list[RelationTypeReadDTO]


class SchemaRefreshResultDTO(BaseModel):
    entity_types: list[str]
    relation_types: list[str]


class EntityTypeCreateDTO(BaseModel):
    type_name: str = Field(min_length=1)


class RelationTypeCreateDTO(BaseModel):
    relation_name: str = Field(min_length=1)


class RenameDTO(BaseModel):
    new_name: str = Field(min_length=1)
