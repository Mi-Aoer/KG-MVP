import json

from sqlalchemy import select

from app.models.sqlite_models import ExtractedTriple
from app.services import parse_service


def test_reparse_source_accepts_valid_output(model_factory, db_session):
    raw_response = json.dumps(
        {
            "output": json.dumps(
                [
                    {
                        "subject": "失眠症",
                        "subject_type": "疾病",
                        "predicate": "辅助治疗",
                        "object": "引导意象和冥想",
                        "object_type": "其他治疗",
                    }
                ],
                ensure_ascii=False,
            )
        },
        ensure_ascii=False,
    )
    context = model_factory.create_source_context(raw_response=raw_response)

    result = parse_service.reparse_source(db_session, context.source.id)
    triples = db_session.scalars(
        select(ExtractedTriple).where(
            ExtractedTriple.source_id == context.source.id,
            ExtractedTriple.status == "valid",
        )
    ).all()

    assert result["parse_status"] == "success"
    assert result["triple_count"] == 1
    assert len(triples) == 1
    assert triples[0].subject == "失眠症"


def test_reparse_source_accepts_empty_array(model_factory, db_session):
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": "[]"}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "success"
    assert result["triple_count"] == 0


def test_reparse_source_rejects_missing_output(model_factory, db_session):
    context = model_factory.create_source_context(
        raw_response=json.dumps({"message": "missing output"}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "failed"
    assert result["error_message"] == "OUTPUT_FIELD_MISSING"


def test_reparse_source_rejects_non_string_output(model_factory, db_session):
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": []}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "failed"
    assert result["error_message"] == "OUTPUT_TYPE_INVALID"


def test_reparse_source_accepts_markdown_json_block(model_factory, db_session):
    markdown_output = """```json
[
  {
    "subject": "焦虑症",
    "subject_type": "疾病",
    "predicate": "辅助治疗",
    "object": "心理治疗",
    "object_type": "其他治疗"
  }
]
```"""
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": markdown_output}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "success"
    assert result["triple_count"] == 1


def test_reparse_source_rejects_invalid_json_output(model_factory, db_session):
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": "[{"}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "failed"
    assert result["error_message"] == "INVALID_JSON_OUTPUT"


def test_reparse_source_rejects_missing_triple_field(model_factory, db_session):
    context = model_factory.create_source_context(
        raw_response=json.dumps(
            {
                "output": json.dumps(
                    [
                        {
                            "subject": "胃炎",
                            "subject_type": "疾病",
                            "predicate": "辅助治疗",
                            "object": "饮食管理",
                        }
                    ],
                    ensure_ascii=False,
                )
            },
            ensure_ascii=False,
        )
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "failed"
    assert result["error_message"] == "TRIPLE_FIELD_MISSING:object_type"
