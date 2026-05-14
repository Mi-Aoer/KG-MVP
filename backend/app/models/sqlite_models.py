from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils.id_utils import uuid_str
from app.utils.time_utils import utcnow_str


DEFAULT_MODEL_TIMEOUT_SECONDS = 180


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    config_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_MODEL_TIMEOUT_SECONDS,
    )
    provider_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )

    __table_args__ = (
        UniqueConstraint("config_type", "name", name="uq_model_configs_type_name"),
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extract_config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("model_configs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    qa_config_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("model_configs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )
    last_import_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parse_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )

    __table_args__ = (
        Index("idx_import_batches_project_status", "project_id", "status"),
    )


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    request_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    parse_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    is_manual_edited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "line_no", name="uq_source_records_batch_line_no"),
        Index("idx_source_records_batch", "batch_id"),
        Index(
            "idx_source_records_batch_status",
            "batch_id",
            "request_status",
            "parse_status",
        ),
    )


class ExtractedTriple(Base):
    __tablename__ = "extracted_triples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("source_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    triple_key: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    subject_type: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="valid")
    is_manual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )

    __table_args__ = (
        Index("idx_extracted_triples_source_id", "source_id"),
        Index("idx_extracted_triples_project_key", "project_id", "triple_key"),
        Index(
            "idx_extracted_triples_project_spo",
            "project_id",
            "subject",
            "predicate",
            "object",
        ),
    )


class EntityType(Base):
    __tablename__ = "entity_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    type_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "type_name", name="uq_entity_types_project_name"),
    )


class RelationType(Base):
    __tablename__ = "relation_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=utcnow_str,
        onupdate=utcnow_str,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "relation_name", name="uq_relation_types_project_name"),
    )


class GraphImportLog(Base):
    __tablename__ = "graph_import_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_relation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduplicated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)
    finished_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_graph_import_logs_project_created", "project_id", "created_at"),
    )


class QALog(Base):
    __tablename__ = "qa_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_cypher: Mapped[str | None] = mapped_column(Text, nullable=True)
    cypher_validation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="invalid",
    )
    query_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)

    __table_args__ = (
        Index("idx_qa_logs_project_created", "project_id", "created_at"),
    )


class ApiErrorLog(Base):
    __tablename__ = "api_error_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_code: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utcnow_str)

    __table_args__ = (
        Index("idx_api_error_logs_module_created", "module", "created_at"),
    )
