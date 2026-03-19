from sqlalchemy import select

from app.models.sqlite_models import SourceRecord
from app.services import batch_service


def test_upload_txt_batch_splits_regular_lines(model_factory, db_session):
    project = model_factory.create_project()

    batch = batch_service.upload_txt_batch(
        db_session,
        project.id,
        "regular.txt",
        "第一行\n第二行".encode("utf-8"),
    )

    sources = db_session.scalars(
        select(SourceRecord)
        .where(SourceRecord.batch_id == batch["id"])
        .order_by(SourceRecord.line_no.asc())
    ).all()

    assert batch["total_lines"] == 2
    assert batch["valid_lines"] == 2
    assert [item.line_no for item in sources] == [1, 2]
    assert [item.input_text for item in sources] == ["第一行", "第二行"]


def test_upload_txt_batch_ignores_blank_lines_and_preserves_original_line_numbers(
    model_factory,
    db_session,
):
    project = model_factory.create_project()

    batch = batch_service.upload_txt_batch(
        db_session,
        project.id,
        "blank-lines.txt",
        "第一行\n\n   \n第四行".encode("utf-8"),
    )

    sources = db_session.scalars(
        select(SourceRecord)
        .where(SourceRecord.batch_id == batch["id"])
        .order_by(SourceRecord.line_no.asc())
    ).all()

    assert batch["total_lines"] == 4
    assert batch["valid_lines"] == 2
    assert [item.line_no for item in sources] == [1, 4]


def test_upload_txt_batch_handles_utf8_bom(model_factory, db_session):
    project = model_factory.create_project()

    batch = batch_service.upload_txt_batch(
        db_session,
        project.id,
        "bom.txt",
        "\ufeff第一行\n第二行".encode("utf-8"),
    )

    first_source = db_session.scalar(
        select(SourceRecord)
        .where(SourceRecord.batch_id == batch["id"])
        .order_by(SourceRecord.line_no.asc())
    )

    assert batch["total_lines"] == 2
    assert batch["valid_lines"] == 2
    assert first_source is not None
    assert first_source.input_text == "第一行"


def test_upload_txt_batch_handles_trailing_newline(model_factory, db_session):
    project = model_factory.create_project()

    batch = batch_service.upload_txt_batch(
        db_session,
        project.id,
        "trailing-newline.txt",
        "第一行\n".encode("utf-8"),
    )

    sources = db_session.scalars(
        select(SourceRecord)
        .where(SourceRecord.batch_id == batch["id"])
        .order_by(SourceRecord.line_no.asc())
    ).all()

    assert batch["total_lines"] == 1
    assert batch["valid_lines"] == 1
    assert [item.line_no for item in sources] == [1]
