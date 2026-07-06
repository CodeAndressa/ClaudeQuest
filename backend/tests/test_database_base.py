from sqlalchemy import Column, String

from app.database.base import AuditedModel


class _SampleModel(AuditedModel):
    """Modelo de exemplo usado apenas para validar as colunas obrigatórias do mixin."""

    __tablename__ = "_sample_model_for_tests"

    name = Column(String, nullable=False)


def test_audited_model_declares_the_mandatory_governance_columns() -> None:
    columns = {column.name for column in _SampleModel.__table__.columns}

    assert columns == {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "version",
        "name",
    }


def test_audited_model_id_is_generated_as_a_uuid_by_default() -> None:
    id_column = _SampleModel.__table__.columns["id"]

    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert id_column.default is not None
    assert id_column.default.is_callable is True


def test_audited_model_version_defaults_to_one() -> None:
    version_column = _SampleModel.__table__.columns["version"]

    assert version_column.default.arg == 1
    assert version_column.nullable is False
