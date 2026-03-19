from fastapi import BackgroundTasks

from app.services import extraction_service


def test_retry_single_source_allows_successful_source(model_factory, db_session):
    project = model_factory.create_project()
    batch = model_factory.create_batch(project_id=project.id, status="success")
    source = model_factory.create_source(
        project_id=project.id,
        batch_id=batch.id,
        request_status="success",
        parse_status="success",
        request_payload='{"model":"demo"}',
        raw_response='{"output":"[]"}',
        cleaned_output_text="[]",
        error_message="old error",
    )
    background_tasks = BackgroundTasks()

    result = extraction_service.retry_single_source(db_session, background_tasks, source.id)

    db_session.refresh(batch)
    db_session.refresh(source)

    assert result == {"batch_id": batch.id, "status": "extracting", "queued": 1}
    assert batch.status == "extracting"
    assert batch.finished_at is None
    assert source.request_status == "pending"
    assert source.parse_status == "pending"
    assert source.request_payload is None
    assert source.raw_response is None
    assert source.cleaned_output_text is None
    assert source.error_message is None
    assert len(background_tasks.tasks) == 1
