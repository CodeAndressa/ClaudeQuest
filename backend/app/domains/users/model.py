import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditedModel


class UserRole(enum.StrEnum):
    STUDENT = "student"
    ADMIN = "admin"


class UserStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class User(AuditedModel):
    """Usuário da plataforma (03 - Functional Specification, Módulo de Autenticação)."""

    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    avatar: Mapped[str | None] = mapped_column(default=None)
    language: Mapped[str] = mapped_column(nullable=False, default="pt-BR")
    timezone: Mapped[str] = mapped_column(nullable=False, default="America/Sao_Paulo")
    country: Mapped[str | None] = mapped_column(default=None)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        nullable=False,
        default=UserRole.STUDENT,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=True),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    email_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
