"""Recuperação de senha (AUTH-003).

Reúne, num único arquivo, model + repository + service + schemas do fluxo de
"esqueci minha senha" — decisão deliberada para minimizar sobreposição com
model.py/service.py/router.py/repository.py do domínio auth, tocados em paralelo
por outra tarefa (refresh/logout). Reaproveita User, hash_password e o padrão de
token opaco (hash SHA-256 persistido) já usado em Session/refresh_token.

Ver 03 - Functional Specification (Módulo de Autenticação: "Recuperação de senha",
"Alteração de senha") e 12 - API (endpoints /auth/forgot-password, /auth/reset-password).
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, ForeignKey, select
from sqlalchemy import Uuid as UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.database.base import AuditedModel
from app.domains.auth.repository import SessionRepository
from app.domains.users.model import User, UserStatus
from app.domains.users.repository import UserRepository
from app.shared.errors import AppError

logger = get_logger(__name__)

RESET_TOKEN_EXPIRE_MINUTES = 30

_INVALID_RESET_TOKEN = AppError(
    code="invalid_reset_token",
    message="Link de recuperação inválido ou expirado.",
    status_code=400,
)


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


class PasswordResetToken(AuditedModel):
    """Token opaco de recuperação de senha — apenas o hash SHA-256 é persistido,
    análogo ao refresh_token_hash em Session (app/domains/auth/model.py)."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


# --------------------------------------------------------------------------- #
# Token helpers (análogos a generate_refresh_token/hash_refresh_token)
# --------------------------------------------------------------------------- #


def generate_reset_token() -> tuple[str, str]:
    """Gera um token opaco de reset. Retorna (token em texto puro, hash para persistir)."""
    token = secrets.token_urlsafe(48)
    return token, hash_reset_token(token)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reset_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class PasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(reset_token)
        await self._session.flush()
        return reset_token

    async def get_valid_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        statement = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_used(self, reset_token: PasswordResetToken) -> None:
        reset_token.used_at = datetime.now(UTC)
        await self._session.flush()


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class PasswordResetService:
    def __init__(
        self,
        users: UserRepository,
        reset_tokens: PasswordResetRepository,
        sessions: SessionRepository,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens
        self._sessions = sessions

    async def forgot_password(self, request: ForgotPasswordRequest) -> None:
        """Sempre retorna sem erro — nunca revela se o e-mail está cadastrado."""
        user = await self._users.get_by_email(request.email)
        if user is None or user.status != UserStatus.ACTIVE:
            return

        token, token_hash = generate_reset_token()
        await self._reset_tokens.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=reset_token_expiry(),
        )

        self._log_reset_link(user, token)

    async def reset_password(self, request: ResetPasswordRequest) -> None:
        reset_token = await self._reset_tokens.get_valid_by_token_hash(
            hash_reset_token(request.token)
        )
        if reset_token is None:
            raise _INVALID_RESET_TOKEN

        user = await self._users.get_by_id(reset_token.user_id)
        if user is None:
            raise _INVALID_RESET_TOKEN

        user.password_hash = hash_password(request.new_password)
        await self._reset_tokens.mark_used(reset_token)
        await self._sessions.revoke_all_for_user(user.id)

    def _log_reset_link(self, user: User, token: str) -> None:
        settings = get_settings()
        reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        logger.info(
            "password_reset_link_generated",
            user_id=str(user.id),
            email=user.email,
            reset_link=reset_link,
        )
