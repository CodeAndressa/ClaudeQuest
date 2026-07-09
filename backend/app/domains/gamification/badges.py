"""Badges (GAME-002).

Reúne, num único arquivo, models + repository + service + schemas do catálogo de
badges e das concessões a usuários — decisão deliberada para minimizar
sobreposição com model.py/service.py/router.py/repository.py/schemas.py do
domínio gamification, tocados em paralelo por outra tarefa (GAME-001, XP). Mesmo
padrão já usado em app/domains/auth/password_reset.py.

Fonte de verdade das regras de negócio: Vault do Obsidian,
`G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\Gamification.md.md`
(seção "Badges": categorias Bronze/Prata/Ouro/Platina/Diamante/Lendário, exemplos
"Primeiro Login", "Primeira Missão", "100 Missões" etc).

Limitação deliberada (ver relatório final da tarefa): a documentação sugere
badges concedidos automaticamente por marcos de progresso (ex.: "100 Missões",
"365 Dias"). Esse gatilho automático dependeria de um sistema de
progresso/tentativas (Attempts/Missions) que ainda não existe no projeto — não
há nenhuma tabela desse tipo no domínio `learning` nem em qualquer outro
domínio hoje. Por isso, este módulo implementa apenas a infraestrutura real:
catálogo de badges + concessão manual via API (mesmo padrão de GAME-001, onde
XP também é concedido via POST manual, não automaticamente por uma missão
concluída). A automação de concessão por marcos fica para quando o sistema de
progresso existir.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, select
from sqlalchemy import Uuid as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import AuditedModel
from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.users.model import User, UserRole
from app.shared.errors import AppError
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


class BadgeCategory(enum.StrEnum):
    """Categorias/raridade de badge, conforme a seção "Categorias" da documentação."""

    BRONZE = "bronze"
    PRATA = "prata"
    OURO = "ouro"
    PLATINA = "platina"
    DIAMANTE = "diamante"
    LENDARIO = "lendario"


class Badge(AuditedModel):
    """Um badge do catálogo — marco possível de ser conquistado por um usuário."""

    __tablename__ = "badges"

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    image: Mapped[str | None] = mapped_column(default=None)
    category: Mapped[BadgeCategory] = mapped_column(
        Enum(
            BadgeCategory,
            name="badge_category",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )


class UserBadge(AuditedModel):
    """Concessão de um badge a um usuário — cada par (user, badge) é único.

    Não há coluna de progresso aqui de propósito: como não existe ainda um
    sistema de Attempts/Progress no projeto, a concessão é sempre um evento
    binário e manual (concedido ou não), nunca calculado a partir de contagem
    de missões/tentativas. Ver docstring do módulo.
    """

    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    badge: Mapped[Badge] = relationship(Badge, lazy="joined")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class BadgeResponse(BaseModel):
    """Um badge do catálogo, para listagem pública."""

    id: UUID
    name: str
    description: str
    image: str | None
    category: BadgeCategory

    model_config = {"from_attributes": True}


class UserBadgeResponse(BaseModel):
    """Um badge conquistado por um usuário, com os dados do badge embutidos."""

    id: UUID
    badge_id: UUID
    earned_at: datetime
    badge: BadgeResponse

    model_config = {"from_attributes": True}


class AwardBadgeRequest(BaseModel):
    """Requisição de concessão manual de um badge a um usuário (admin-only)."""

    user_id: UUID


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

_BADGE_NOT_FOUND = AppError(
    code="badge_not_found",
    message="Badge não encontrado.",
    status_code=404,
)

_BADGE_ALREADY_AWARDED = AppError(
    code="badge_already_awarded",
    message="Este usuário já possui este badge — não é possível concedê-lo novamente.",
    status_code=409,
)

_FORBIDDEN = AppError(
    code="forbidden",
    message="Apenas administradores podem conceder badges.",
    status_code=403,
)


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class BadgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Badge]:
        statement = select(Badge).where(Badge.deleted_at.is_(None)).order_by(Badge.created_at)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, badge_id: UUID) -> Badge | None:
        statement = select(Badge).where(Badge.id == badge_id, Badge.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        description: str,
        category: BadgeCategory,
        image: str | None = None,
    ) -> Badge:
        badge = Badge(name=name, description=description, category=category, image=image)
        self._session.add(badge)
        await self._session.flush()
        return badge


class UserBadgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: UUID) -> list[UserBadge]:
        statement = (
            select(UserBadge)
            .where(UserBadge.user_id == user_id, UserBadge.deleted_at.is_(None))
            .order_by(UserBadge.earned_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_for_user_and_badge(self, *, user_id: UUID, badge_id: UUID) -> UserBadge | None:
        statement = select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_id == badge_id,
            UserBadge.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, *, user_id: UUID, badge_id: UUID) -> UserBadge:
        user_badge = UserBadge(user_id=user_id, badge_id=badge_id, earned_at=datetime.now(UTC))
        self._session.add(user_badge)
        await self._session.flush()
        # `badge` é `lazy="joined"`, mas isso só se aplica a queries feitas via `select()` —
        # um objeto recém-criado por `add()+flush()` não tem a relação carregada. Sem este
        # refresh explícito, acessar `user_badge.badge` fora de um contexto já resolvido
        # (ex.: dentro do Pydantic `model_validate` no router) lança `MissingGreenlet`,
        # porque o SQLAlchemy tenta um lazy-load síncrono implícito em código assíncrono.
        await self._session.refresh(user_badge, attribute_names=["badge"])
        return user_badge


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class BadgeService:
    def __init__(self, badges: BadgeRepository, user_badges: UserBadgeRepository) -> None:
        self._badges = badges
        self._user_badges = user_badges

    async def list_catalog(self) -> list[Badge]:
        return await self._badges.list_all()

    async def list_for_user(self, user_id: UUID) -> list[UserBadge]:
        return await self._user_badges.list_for_user(user_id)

    async def award(self, *, badge_id: UUID, user_id: UUID) -> UserBadge:
        badge = await self._badges.get_by_id(badge_id)
        if badge is None:
            raise _BADGE_NOT_FOUND

        existing = await self._user_badges.get_for_user_and_badge(
            user_id=user_id, badge_id=badge_id
        )
        if existing is not None:
            raise _BADGE_ALREADY_AWARDED

        return await self._user_badges.create(user_id=user_id, badge_id=badge_id)


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
#
# Registrado à parte do router principal de gamification (app/domains/gamification/
# router.py), que pertence à tarefa GAME-001 em andamento em paralelo — este router
# é incluído diretamente em app/api/v1/router.py com o mesmo prefixo "/gamification"
# para expor os endpoints sob o mesmo namespace de API sem editar arquivos
# concorrentes.

badges_router = APIRouter(prefix="/gamification", tags=["gamification", "badges"])


def get_badge_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BadgeService:
    return BadgeService(BadgeRepository(session), UserBadgeRepository(session))


@badges_router.get("/badges")
async def list_badge_catalog(
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
    badge_service: Annotated[BadgeService, Depends(get_badge_service)],
) -> SuccessResponse[list[BadgeResponse]]:
    badges = await badge_service.list_catalog()
    data = [BadgeResponse.model_validate(badge) for badge in badges]
    return success_response(request, "Catálogo de badges recuperado com sucesso.", data)


@badges_router.get("/me/badges")
async def list_my_badges(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    badge_service: Annotated[BadgeService, Depends(get_badge_service)],
) -> SuccessResponse[list[UserBadgeResponse]]:
    user_badges = await badge_service.list_for_user(current_user.id)
    data = [UserBadgeResponse.model_validate(user_badge) for user_badge in user_badges]
    return success_response(request, "Badges do usuário recuperados com sucesso.", data)


@badges_router.post("/badges/{badge_id}/award")
async def award_badge(
    request: Request,
    badge_id: UUID,
    payload: AwardBadgeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    badge_service: Annotated[BadgeService, Depends(get_badge_service)],
) -> SuccessResponse[UserBadgeResponse]:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN

    user_badge = await badge_service.award(badge_id=badge_id, user_id=payload.user_id)
    data = UserBadgeResponse.model_validate(user_badge)
    return success_response(request, "Badge concedido com sucesso.", data)
