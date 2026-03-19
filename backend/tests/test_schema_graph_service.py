from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.models.sqlite_models import EntityType, ExtractedTriple, GraphImportLog, RelationType
from app.services import graph_service, schema_service
from app.utils.hash_utils import make_triple_key


class FakeCounters:
    def __init__(self, *, nodes_created=0, relationships_created=0):
        self.nodes_created = nodes_created
        self.relationships_created = relationships_created


class FakeResult:
    def __init__(self, *, nodes_created=0, relationships_created=0):
        self._summary = SimpleNamespace(
            counters=FakeCounters(
                nodes_created=nodes_created,
                relationships_created=relationships_created,
            )
        )

    def consume(self):
        return self._summary


class FakeTransaction:
    def __init__(self, graph_state):
        self.graph_state = graph_state
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type
        del exc
        del tb
        return False

    def run(self, query, **params):
        self.queries.append((query, params))
        if "DETACH DELETE" in query:
            project_id = params["project_id"]
            self.graph_state["nodes"] = {
                key for key in self.graph_state["nodes"] if key[0] != project_id
            }
            self.graph_state["relationships"] = {
                key for key in self.graph_state["relationships"] if key[0] != project_id
            }
            return FakeResult()

        if "MERGE (s:KGEntity" not in query:
            return FakeResult()

        subject_key = (params["project_id"], params["subject_type"], params["subject"])
        object_key = (params["project_id"], params["object_type"], params["object"])
        relationship_key = (
            params["project_id"],
            subject_key,
            params["predicate"],
            object_key,
        )

        created_nodes = 0
        if subject_key not in self.graph_state["nodes"]:
            self.graph_state["nodes"].add(subject_key)
            created_nodes += 1
        if object_key not in self.graph_state["nodes"]:
            self.graph_state["nodes"].add(object_key)
            created_nodes += 1

        created_relationships = 0
        if relationship_key not in self.graph_state["relationships"]:
            self.graph_state["relationships"].add(relationship_key)
            created_relationships += 1

        return FakeResult(
            nodes_created=created_nodes,
            relationships_created=created_relationships,
        )

    def commit(self):
        return None


class FakeSession:
    def __init__(self, graph_state):
        self.graph_state = graph_state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type
        del exc
        del tb
        return False

    def begin_transaction(self):
        return FakeTransaction(self.graph_state)

    def run(self, query, **params):
        return FakeTransaction(self.graph_state).run(query, **params)


class FakeDriver:
    def __init__(self):
        self.graph_state = {"nodes": set(), "relationships": set()}

    def session(self):
        return FakeSession(self.graph_state)


def test_refresh_schema_adds_missing_names(model_factory, db_session):
    context = model_factory.create_source_context(project_status="imported")
    model_factory.create_triple(
        project_id=context.project.id,
        batch_id=context.batch.id,
        source_id=context.source.id,
        subject="失眠症",
        subject_type="疾病",
        predicate="辅助治疗",
        object_="冥想",
        object_type="其他治疗",
    )

    result = schema_service.refresh_schema(db_session, context.project.id)
    db_session.refresh(context.project)

    assert set(result["entity_types"]) == {"疾病", "其他治疗"}
    assert set(result["relation_types"]) == {"辅助治疗"}
    assert context.project.status == "initialized"


def test_delete_entity_type_in_use_is_blocked(model_factory, db_session):
    context = model_factory.create_source_context()
    model_factory.create_triple(
        project_id=context.project.id,
        batch_id=context.batch.id,
        source_id=context.source.id,
        subject="失眠症",
        subject_type="疾病",
        predicate="辅助治疗",
        object_="冥想",
        object_type="其他治疗",
    )
    schema_service.refresh_schema(db_session, context.project.id)
    entity_type = db_session.scalar(
        select(EntityType).where(
            EntityType.project_id == context.project.id,
            EntityType.type_name == "疾病",
        )
    )

    with pytest.raises(AppError) as exc_info:
        schema_service.delete_entity_type(db_session, entity_type.id)

    assert exc_info.value.message == "ENTITY_TYPE_IN_USE"


def test_rename_relation_type_updates_triples_and_marks_project_dirty(model_factory, db_session):
    context = model_factory.create_source_context(project_status="imported")
    triple = model_factory.create_triple(
        project_id=context.project.id,
        batch_id=context.batch.id,
        source_id=context.source.id,
        subject="失眠症",
        subject_type="疾病",
        predicate="辅助治疗",
        object_="冥想",
        object_type="其他治疗",
        imported=1,
    )
    schema_service.refresh_schema(db_session, context.project.id)
    relation_type = db_session.scalar(
        select(RelationType).where(
            RelationType.project_id == context.project.id,
            RelationType.relation_name == "辅助治疗",
        )
    )

    result = schema_service.rename_relation_type(db_session, relation_type.id, "治疗方式")
    db_session.refresh(triple)
    db_session.refresh(context.project)

    assert result["relation_name"] == "治疗方式"
    assert triple.predicate == "治疗方式"
    assert triple.triple_key == make_triple_key(context.project.id, "失眠症", "治疗方式", "冥想")
    assert triple.imported == 0
    assert context.project.status == "initialized"


def test_graph_init_import_and_rebuild_follow_project_level_rules(
    monkeypatch,
    model_factory,
    db_session,
):
    fake_driver = FakeDriver()
    monkeypatch.setattr(graph_service, "get_driver", lambda: fake_driver)
    monkeypatch.setattr(graph_service, "verify_connectivity", lambda: None)

    context = model_factory.create_source_context()
    triple_a = model_factory.create_triple(
        project_id=context.project.id,
        batch_id=context.batch.id,
        source_id=context.source.id,
        subject="失眠症",
        subject_type="疾病",
        predicate="辅助治疗",
        object_="冥想",
        object_type="其他治疗",
    )
    triple_b = model_factory.create_triple(
        project_id=context.project.id,
        batch_id=context.batch.id,
        source_id=context.source.id,
        subject="失眠症",
        subject_type="疾病",
        predicate="辅助治疗",
        object_="冥想",
        object_type="其他治疗",
    )

    init_result = graph_service.init_graph(db_session, context.project.id)
    import_result = graph_service.import_graph(db_session, context.project.id, mode="incremental")

    assert init_result["status"] == "initialized"
    assert import_result["total_candidate_count"] == 2
    assert import_result["created_node_count"] == 2
    assert import_result["created_relation_count"] == 1
    assert import_result["deduplicated_count"] == 1
    assert import_result["failed_count"] == 0

    db_session.refresh(triple_a)
    db_session.refresh(triple_b)
    assert triple_a.imported == 1
    assert triple_b.imported == 1

    extra_triple = model_factory.create_triple(
        project_id=context.project.id,
        batch_id=context.batch.id,
        source_id=context.source.id,
        subject="焦虑症",
        subject_type="疾病",
        predicate="辅助治疗",
        object_="心理治疗",
        object_type="其他治疗",
    )
    context.project.status = "initialized"
    db_session.commit()

    rebuild_result = graph_service.import_graph(db_session, context.project.id, mode="rebuild")
    db_session.refresh(extra_triple)

    assert rebuild_result["mode"] == "rebuild"
    assert rebuild_result["total_candidate_count"] == 3
    assert rebuild_result["created_relation_count"] == 2
    assert rebuild_result["deduplicated_count"] == 1
    assert extra_triple.imported == 1

    import_logs = db_session.scalars(
        select(GraphImportLog).where(GraphImportLog.project_id == context.project.id)
    ).all()
    assert len(import_logs) == 2
