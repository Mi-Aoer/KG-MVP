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


def test_reparse_source_strips_think_block(model_factory, db_session):
    output = """<think>
I should reason about the extraction first.
</think>
[
  {
    "subject": "MQ-8C",
    "subject_type": "Asset",
    "predicate": "tested_by",
    "object": "US Navy",
    "object_type": "Actor"
  }
]"""
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": output}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "success"
    assert result["triple_count"] == 1
    assert context.source.cleaned_output_text.startswith("[")
    assert "<think>" not in context.source.cleaned_output_text


def test_reparse_source_extracts_json_array_from_descriptive_text(model_factory, db_session):
    output = """以下是根据问题中提取的各个关系：

```json
[
  {
    "subject": "大地-1导弹",
    "subject_type": "Asset",
    "predicate": "tested_by",
    "object": "印度",
    "object_type": "Actor"
  },
  {
    "subject": "大地-1导弹",
    "subject_type": "Asset",
    "predicate": "occurs_on",
    "object": "5月12日下午1时4分",
    "object_type": "Time"
  }
]
```

这些关系涵盖了试验的时间、地点、测试者等关键信息。"""
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": output}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "success"
    assert result["triple_count"] == 2
    assert context.source.cleaned_output_text.startswith("[")
    assert context.source.cleaned_output_text.endswith("]")


def test_reparse_source_skips_non_object_arrays_before_triples(model_factory, db_session):
    output = """候选实体类型包括 ["Actor", "Asset", "Time"]。
最终关系如下：
[
  {
    "subject": "大地-1导弹",
    "subject_type": "Asset",
    "predicate": "occurs_at",
    "object": "昌迪普尔海上试验场",
    "object_type": "Place"
  }
]"""
    context = model_factory.create_source_context(
        raw_response=json.dumps({"output": output}, ensure_ascii=False)
    )

    result = parse_service.reparse_source(db_session, context.source.id)

    assert result["parse_status"] == "success"
    assert result["triple_count"] == 1
    assert '"Actor"' not in context.source.cleaned_output_text


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
