from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.neo4j_client import get_driver, verify_connectivity
from app.models.sqlite_models import ExtractedTriple, GraphImportLog, Project, SourceRecord
from app.schemas.graph import GraphImportLogReadDTO, GraphImportResultDTO, GraphInitResultDTO
from app.services.api_error_log_service import log_api_error
from app.utils.time_utils import utcnow_str


KG_ENTITY_CONSTRAINT_CYPHER = """
CREATE CONSTRAINT kg_entity_unique IF NOT EXISTS
FOR (n:KGEntity)
REQUIRE (n.project_id, n.entity_type, n.name) IS UNIQUE
"""

DELETE_PROJECT_GRAPH_CYPHER = """
MATCH (n:KGEntity {project_id: $project_id})
DETACH DELETE n
"""

UPSERT_TRIPLE_CYPHER = """
MERGE (s:KGEntity {
  project_id: $project_id,
  entity_type: $subject_type,
  name: $subject
})
ON CREATE SET s.created_at = $now
SET s.updated_at = $now
MERGE (o:KGEntity {
  project_id: $project_id,
  entity_type: $object_type,
  name: $object
})
ON CREATE SET o.created_at = $now
SET o.updated_at = $now
MERGE (s)-[r:RELATED_TO {
  project_id: $project_id,
  predicate: $predicate
}]->(o)
ON CREATE SET
  r.first_batch_id = $batch_id,
  r.first_source_id = $source_id,
  r.first_line_no = $line_no,
  r.created_at = $now
SET r.updated_at = $now
"""


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", code=4041, status_code=404)
    return project


def _serialize_graph_init_result(project: Project) -> dict:
    return GraphInitResultDTO(project_id=project.id, status=project.status).model_dump()


def _serialize_import_result(log: GraphImportLog) -> dict:
    return GraphImportResultDTO(
        import_log_id=log.id,
        mode=log.mode,
        status=log.status,
        total_candidate_count=log.total_candidate_count,
        created_node_count=log.created_node_count,
        created_relation_count=log.created_relation_count,
        deduplicated_count=log.deduplicated_count,
        failed_count=log.failed_count,
    ).model_dump()


def _serialize_import_log(log: GraphImportLog) -> dict:
    return GraphImportLogReadDTO(
        id=log.id,
        project_id=log.project_id,
        mode=log.mode,
        status=log.status,
        total_candidate_count=log.total_candidate_count,
        created_node_count=log.created_node_count,
        created_relation_count=log.created_relation_count,
        deduplicated_count=log.deduplicated_count,
        failed_count=log.failed_count,
        error_message=log.error_message,
        created_at=log.created_at,
        finished_at=log.finished_at,
    ).model_dump()


def _ensure_project_ready_for_import(project: Project) -> None:
    if project.status in {"initialized", "imported"}:
        return
    raise AppError("GRAPH_NOT_INITIALIZED", code=4099, status_code=409)


def _normalize_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _ensure_graph_constraint() -> None:
    driver = get_driver()
    with driver.session() as session:
        session.run(KG_ENTITY_CONSTRAINT_CYPHER).consume()


def _run_delete_project_graph(project_id: str) -> None:
    driver = get_driver()
    with driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run(DELETE_PROJECT_GRAPH_CYPHER, project_id=project_id).consume()
            tx.commit()


def _load_valid_triples(db: Session, project_id: str) -> list[dict]:
    stmt = (
        select(
            ExtractedTriple.id,
            ExtractedTriple.subject,
            ExtractedTriple.subject_type,
            ExtractedTriple.predicate,
            ExtractedTriple.object,
            ExtractedTriple.object_type,
            ExtractedTriple.batch_id,
            ExtractedTriple.source_id,
            SourceRecord.line_no,
        )
        .join(SourceRecord, SourceRecord.id == ExtractedTriple.source_id)
        .where(
            ExtractedTriple.project_id == project_id,
            ExtractedTriple.status == "valid",
        )
        .order_by(
            ExtractedTriple.created_at.asc(),
            SourceRecord.line_no.asc(),
            ExtractedTriple.id.asc(),
        )
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": row.id,
            "subject": row.subject,
            "subject_type": row.subject_type,
            "predicate": row.predicate,
            "object": row.object,
            "object_type": row.object_type,
            "batch_id": row.batch_id,
            "source_id": row.source_id,
            "line_no": row.line_no,
        }
        for row in rows
    ]


def _group_candidate_triples(rows: Iterable[dict]) -> tuple[list[dict], int]:
    grouped: dict[tuple[str, str, str], dict] = {}
    total_count = 0

    for row in rows:
        total_count += 1
        key = (row["subject"], row["predicate"], row["object"])
        current = grouped.get(key)
        if current is None:
            grouped[key] = {
                "subject": row["subject"],
                "subject_type": row["subject_type"],
                "predicate": row["predicate"],
                "object": row["object"],
                "object_type": row["object_type"],
                "batch_id": row["batch_id"],
                "source_id": row["source_id"],
                "line_no": row["line_no"],
                "triple_ids": [row["id"]],
                "conflict": False,
            }
            continue

        current["triple_ids"].append(row["id"])
        if (
            current["subject_type"] != row["subject_type"]
            or current["object_type"] != row["object_type"]
        ):
            current["conflict"] = True

    grouped_items = list(grouped.values())
    deduplicated_count = max(0, total_count - len(grouped_items))
    return grouped_items, deduplicated_count


def _create_import_log(db: Session, project_id: str, mode: str, total_candidate_count: int) -> str:
    import_log = GraphImportLog(
        project_id=project_id,
        mode=mode,
        status="pending",
        total_candidate_count=total_candidate_count,
    )
    db.add(import_log)
    db.commit()
    return import_log.id


def _mark_import_log_failed(
    db: Session,
    import_log_id: str,
    *,
    deduplicated_count: int,
    failed_count: int,
    error_message: str,
) -> None:
    import_log = db.get(GraphImportLog, import_log_id)
    if import_log is None:
        return
    import_log.status = "failed"
    import_log.deduplicated_count = deduplicated_count
    import_log.failed_count = failed_count
    import_log.error_message = error_message
    import_log.finished_at = utcnow_str()
    db.commit()


def init_graph(db: Session, project_id: str) -> dict:
    project = _get_project_or_404(db, project_id)
    try:
        verify_connectivity()
        _ensure_graph_constraint()
    except Exception as exc:
        error_message = _normalize_error_message(exc)
        log_api_error(
            db,
            module="graph",
            ref_type="project",
            ref_id=project_id,
            error_code="NEO4J_INIT_FAILED",
            error_message=error_message,
        )
        raise AppError("NEO4J_INIT_FAILED", code=5001, status_code=500) from exc

    project.status = "initialized"
    db.commit()
    db.refresh(project)
    return _serialize_graph_init_result(project)


def import_graph(db: Session, project_id: str, mode: str = "incremental") -> dict:
    if mode not in {"incremental", "rebuild"}:
        raise AppError("INVALID_GRAPH_IMPORT_MODE", code=4012, status_code=400)

    project = _get_project_or_404(db, project_id)
    _ensure_project_ready_for_import(project)

    rows = _load_valid_triples(db, project_id)
    grouped_items, deduplicated_count = _group_candidate_triples(rows)
    import_log_id = _create_import_log(db, project_id, mode, len(rows))

    created_node_count = 0
    created_relation_count = 0
    failed_count = 0
    imported_triple_ids: list[str] = []
    now = utcnow_str()

    try:
        driver = get_driver()
        with driver.session() as session:
            with session.begin_transaction() as tx:
                if mode == "rebuild":
                    tx.run(DELETE_PROJECT_GRAPH_CYPHER, project_id=project_id).consume()

                for item in grouped_items:
                    if item["conflict"]:
                        failed_count += 1
                        continue

                    result = tx.run(
                        UPSERT_TRIPLE_CYPHER,
                        project_id=project_id,
                        subject=item["subject"],
                        subject_type=item["subject_type"],
                        predicate=item["predicate"],
                        object=item["object"],
                        object_type=item["object_type"],
                        batch_id=item["batch_id"],
                        source_id=item["source_id"],
                        line_no=item["line_no"],
                        now=now,
                    )
                    summary = result.consume()
                    created_node_count += summary.counters.nodes_created
                    created_relation_count += summary.counters.relationships_created
                    imported_triple_ids.extend(item["triple_ids"])

                tx.commit()

        valid_triples = db.scalars(
            select(ExtractedTriple).where(
                ExtractedTriple.project_id == project_id,
                ExtractedTriple.status == "valid",
            )
        ).all()
        imported_triple_id_set = set(imported_triple_ids)
        for triple in valid_triples:
            triple.imported = 1 if triple.id in imported_triple_id_set else 0

        import_log = db.get(GraphImportLog, import_log_id)
        if import_log is None:
            raise AppError("GRAPH_IMPORT_LOG_NOT_FOUND", code=4047, status_code=404)

        import_log.status = "success"
        import_log.created_node_count = created_node_count
        import_log.created_relation_count = created_relation_count
        import_log.deduplicated_count = deduplicated_count
        import_log.failed_count = failed_count
        import_log.error_message = None
        import_log.finished_at = now

        project.status = "imported"
        project.last_import_at = now

        db.commit()
        db.refresh(import_log)
        return _serialize_import_result(import_log)
    except AppError:
        db.rollback()
        error_message = "GRAPH_IMPORT_FAILED"
        _mark_import_log_failed(
            db,
            import_log_id,
            deduplicated_count=deduplicated_count,
            failed_count=failed_count,
            error_message=error_message,
        )
        log_api_error(
            db,
            module="graph",
            ref_type="project",
            ref_id=project_id,
            error_code="GRAPH_IMPORT_FAILED",
            error_message=error_message,
            raw_payload={"mode": mode},
        )
        raise
    except Exception as exc:
        db.rollback()
        error_message = _normalize_error_message(exc)
        _mark_import_log_failed(
            db,
            import_log_id,
            deduplicated_count=deduplicated_count,
            failed_count=failed_count,
            error_message=error_message,
        )
        log_api_error(
            db,
            module="graph",
            ref_type="project",
            ref_id=project_id,
            error_code="GRAPH_IMPORT_FAILED",
            error_message=error_message,
            raw_payload={"mode": mode},
        )
        raise AppError("GRAPH_IMPORT_FAILED", code=5003, status_code=500) from exc


def delete_project_graph(project_id: str) -> None:
    try:
        _run_delete_project_graph(project_id)
    except Exception as exc:
        raise AppError("NEO4J_DELETE_FAILED", code=5002, status_code=500) from exc


def list_import_logs(db: Session, project_id: str) -> list[dict]:
    _get_project_or_404(db, project_id)
    stmt = (
        select(GraphImportLog)
        .where(GraphImportLog.project_id == project_id)
        .order_by(GraphImportLog.created_at.desc(), GraphImportLog.id.desc())
    )
    logs = db.scalars(stmt).all()
    return [_serialize_import_log(item) for item in logs]
