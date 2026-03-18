from pydantic import BaseModel


class GraphInitResultDTO(BaseModel):
    project_id: str
    status: str


class GraphImportResultDTO(BaseModel):
    import_log_id: str
    mode: str
    status: str
    total_candidate_count: int
    created_node_count: int
    created_relation_count: int
    deduplicated_count: int
    failed_count: int


class GraphImportLogReadDTO(BaseModel):
    id: str
    project_id: str
    mode: str
    status: str
    total_candidate_count: int
    created_node_count: int
    created_relation_count: int
    deduplicated_count: int
    failed_count: int
    error_message: str | None
    created_at: str
    finished_at: str | None
