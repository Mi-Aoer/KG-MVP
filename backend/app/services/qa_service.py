from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.neo4j_client import get_driver, verify_connectivity
from app.models.sqlite_models import Project
from app.schemas.qa import QAAskRequestDTO, QAAskResultDTO, QAEvidenceDTO
from app.services.api_error_log_service import log_api_error


QA_MATCH_TRIPLES_CYPHER = """
MATCH (s:KGEntity {project_id: $project_id})-[r:RELATED_TO {project_id: $project_id}]->(o:KGEntity {project_id: $project_id})
WHERE toLower($question) CONTAINS toLower(s.name)
   OR toLower($question) CONTAINS toLower(o.name)
   OR toLower($question) CONTAINS toLower(r.predicate)
RETURN
  s.name AS subject,
  s.entity_type AS subject_type,
  r.predicate AS predicate,
  o.name AS object,
  o.entity_type AS object_type,
  coalesce(r.first_source_text, "") AS source_text
LIMIT $limit
"""


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", code=4041, status_code=404)
    return project


def _normalize_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _build_answer(project_name: str, evidence: list[QAEvidenceDTO]) -> str:
    if not evidence:
        return (
            f"在项目“{project_name}”中未检索到与问题直接匹配的关系。"
            "请尝试在问题中包含实体名或关系词。"
        )

    lines: list[str] = []
    for item in evidence[:3]:
        lines.append(
            f"{item.subject}（{item.subject_type}）"
            f" -[{item.predicate}]-> "
            f"{item.object}（{item.object_type}）"
        )
    joined = "；".join(lines)
    return f"在项目“{project_name}”中检索到 {len(evidence)} 条相关关系。示例：{joined}。"


def ask_question(db: Session, project_id: str, payload: QAAskRequestDTO) -> dict:
    project = _get_project_or_404(db, project_id)

    if project.status not in {"initialized", "imported"}:
        raise AppError("GRAPH_NOT_INITIALIZED", code=4099, status_code=409)

    question = payload.question.strip()
    if not question:
        raise AppError("QUESTION_REQUIRED", code=4004, status_code=400)

    try:
        verify_connectivity()
        driver = get_driver()
        with driver.session() as session:
            rows = session.run(
                QA_MATCH_TRIPLES_CYPHER,
                project_id=project_id,
                question=question,
                limit=20,
            ).data()
    except AppError:
        raise
    except Exception as exc:
        error_message = _normalize_error_message(exc)
        log_api_error(
            db,
            module="qa",
            ref_type="project",
            ref_id=project_id,
            error_code="QA_QUERY_FAILED",
            error_message=error_message,
        )
        raise AppError("QA_QUERY_FAILED", code=5005, status_code=500) from exc

    evidence: list[QAEvidenceDTO] = []
    for row in rows:
        subject = row.get("subject")
        subject_type = row.get("subject_type")
        predicate = row.get("predicate")
        obj = row.get("object")
        object_type = row.get("object_type")
        source_text = row.get("source_text")
        if not all(
            isinstance(value, str) and value.strip()
            for value in [subject, subject_type, predicate, obj, object_type]
        ):
            continue
        if not isinstance(source_text, str):
            source_text = ""
        evidence.append(
            QAEvidenceDTO(
                subject=subject.strip(),
                subject_type=subject_type.strip(),
                predicate=predicate.strip(),
                object=obj.strip(),
                object_type=object_type.strip(),
                source_text=source_text.strip(),
            )
        )

    result = QAAskResultDTO(
        project_id=project_id,
        question=question,
        answer=_build_answer(project.name, evidence),
        matched_count=len(evidence),
        evidence=evidence,
    )
    return result.model_dump()
