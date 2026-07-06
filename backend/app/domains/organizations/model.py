from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditedModel


class Organization(AuditedModel):
    """
    Preparação para SaaS multiempresa (05 - Database/Database Specification.md.md).
    O conteúdo educacional permanece global no MVP — ver ADR-011, item 4.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(nullable=False, default="internal")
    status: Mapped[str] = mapped_column(nullable=False, default="active")
