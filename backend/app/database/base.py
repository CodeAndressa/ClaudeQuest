import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM do domínio."""


class AuditedModel(Base):
    """
    Mixin com as colunas obrigatórias em toda tabela do projeto,
    conforme a convenção definida em 05 - Database/Database Specification.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
