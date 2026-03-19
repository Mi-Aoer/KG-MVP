from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.sqlite_models import (
    ExtractedTriple,
    ImportBatch,
    ModelConfig,
    Project,
    SourceRecord,
)
from app.utils.hash_utils import make_triple_key


@pytest.fixture
def db_session(tmp_path) -> Session:
    database_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_fk(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def model_factory(db_session):
    def create_config(**overrides):
        payload = {
            "config_type": "extract",
            "name": "test-extract-config",
            "base_url": "mock://extract",
            "api_key": "sk-test",
            "model_name": "mock-model",
            "timeout_seconds": 60,
            "provider_options": None,
            "is_enabled": 1,
        }
        payload.update(overrides)
        config = ModelConfig(**payload)
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        return config

    def create_project(*, extract_config_id=None, **overrides):
        config = None
        if extract_config_id is None:
            config = create_config()
            extract_config_id = config.id
        payload = {
            "name": f"test-project-{extract_config_id[:8]}",
            "description": "test project",
            "extract_config_id": extract_config_id,
            "status": "ready",
        }
        payload.update(overrides)
        project = Project(**payload)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        return project

    def create_batch(*, project_id, **overrides):
        payload = {
            "project_id": project_id,
            "file_name": "demo.txt",
            "instruction": "请抽取三元组并输出 JSON 数组。",
            "total_lines": 1,
            "valid_lines": 1,
            "status": "uploaded",
            "success_count": 0,
            "request_failed_count": 0,
            "parse_failed_count": 0,
        }
        payload.update(overrides)
        batch = ImportBatch(**payload)
        db_session.add(batch)
        db_session.commit()
        db_session.refresh(batch)
        return batch

    def create_source(*, project_id, batch_id, line_no=1, input_text="示例文本", **overrides):
        payload = {
            "project_id": project_id,
            "batch_id": batch_id,
            "line_no": line_no,
            "input_text": input_text,
            "request_status": "success",
            "parse_status": "pending",
            "is_manual_edited": 0,
            "retry_count": 0,
        }
        payload.update(overrides)
        source = SourceRecord(**payload)
        db_session.add(source)
        db_session.commit()
        db_session.refresh(source)
        return source

    def create_triple(
        *,
        project_id,
        batch_id,
        source_id,
        subject,
        subject_type,
        predicate,
        object_,
        object_type,
        **overrides,
    ):
        payload = {
            "project_id": project_id,
            "batch_id": batch_id,
            "source_id": source_id,
            "triple_key": make_triple_key(project_id, subject, predicate, object_),
            "subject": subject,
            "subject_type": subject_type,
            "predicate": predicate,
            "object": object_,
            "object_type": object_type,
            "status": "valid",
            "is_manual": 0,
            "imported": 0,
        }
        payload.update(overrides)
        triple = ExtractedTriple(**payload)
        db_session.add(triple)
        db_session.commit()
        db_session.refresh(triple)
        return triple

    def create_source_context(
        *,
        project_status="ready",
        raw_response=None,
        input_text="示例文本",
        line_no=1,
    ):
        config = create_config()
        project = create_project(extract_config_id=config.id, status=project_status)
        batch = create_batch(project_id=project.id)
        source = create_source(
            project_id=project.id,
            batch_id=batch.id,
            line_no=line_no,
            input_text=input_text,
            raw_response=raw_response,
        )
        return SimpleNamespace(config=config, project=project, batch=batch, source=source)

    return SimpleNamespace(
        create_config=create_config,
        create_project=create_project,
        create_batch=create_batch,
        create_source=create_source,
        create_triple=create_triple,
        create_source_context=create_source_context,
    )
