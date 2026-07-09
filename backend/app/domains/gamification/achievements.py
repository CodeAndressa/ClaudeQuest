"""Achievements (GAME-003).

Reúne, num único arquivo, models + repository + service + schemas do catálogo de
achievements e das concessões a usuários — mesma decisão deliberada usada em
`badges.py` e `certificates.py` deste domínio, para minimizar sobreposição com
`model.py`/`service.py`/`router.py`/`repository.py`/`schemas.py`, tocados em
paralelo por outras tarefas.

Achievements são DIFERENTES de Badges: a concessão de um Achievement é sempre
automática, calculada a partir de métricas reais de progresso do usuário
(XP total, lições concluídas, badges conquistados, certificados emitidos,
streak de dias consecutivos com atividade) — nunca manual via API. Badges,
por sua vez, continuam sendo concedidos manualmente (ver docstring de
`badges.py`) até que a documentação decida unificar os dois conceitos.

A avaliação é feita sob demanda ("lazy evaluation"): não há job/cron
recalculando achievements em background. Toda vez que
`GET /gamification/me/achievements` é chamado, o service primeiro recalcula as
métricas atuais do usuário e concede qualquer achievement cujo threshold já
tenha sido atingido e ainda não tenha sido registrado, e só depois lista o que
o usuário possui. Mesmo padrão de avaliação preguiçosa usado pelos módulos
`leagues.py`/`quests.py` deste domínio (avaliação disparada na leitura, não em
um worker separado).
"""

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import AuditedModel
from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.gamification.badges import UserBadge
from app.domains.gamification.certificates import UserCertificate
from app.domains.gamification.model import XpLedger
from app.domains.learning.model import UserLessonProgress
from app.domains.users.model import User, UserRole
from app.shared.errors import AppError
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


class AchievementMetric(enum.StrEnum):
    """Métrica usada para avaliar se um `Achievement` deve ser concedido."""

    LESSONS_COMPLETED = "lessons_completed"
    STREAK_DAYS = "streak_days"
    TOTAL_XP = "total_xp"
    BADGES_COUNT = "badges_count"
    CERTIFICATES_COUNT = "certificates_count"


class Achievement(AuditedModel):
    """Uma regra de marco do catálogo de achievements.

    Concedido automaticamente (nunca manualmente) quando a métrica do usuário
    atinge `threshold` — ver docstring do módulo.
    """

    __tablename__ = "achievements"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, nullable=False)
    metric: Mapped[AchievementMetric] = mapped_column(
        Enum(
            AchievementMetric,
            name="achievement_metric",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)


class UserAchievement(AuditedModel):
    """Concessão de um achievement a um usuário — cada par (user, achievement) é único.

    Nasce exclusivamente pela avaliação automática de `AchievementService.evaluate_and_grant`,
    nunca por um endpoint de concessão manual (diferença deliberada em relação a
    `UserBadge`, ver docstring do módulo).
    """

    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievements_user_achievement"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    achievement: Mapped[Achievement] = relationship(Achievement, lazy="joined")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class AchievementResponse(BaseModel):
    """Uma regra de achievement do catálogo, para listagem pública."""

    id: UUID
    name: str
    description: str
    icon: str
    metric: AchievementMetric
    threshold: int

    model_config = {"from_attributes": True}


class UserAchievementResponse(BaseModel):
    """Um achievement conquistado por um usuário, com os dados da regra embutidos."""

    id: UUID
    achievement_id: UUID
    achieved_at: datetime
    achievement: AchievementResponse

    model_config = {"from_attributes": True}


class CreateAchievementRequest(BaseModel):
    """Body de `POST /gamification/achievements` (admin-only)."""

    name: str
    description: str
    icon: str
    metric: AchievementMetric
    threshold: int


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

_FORBIDDEN = AppError(
    code="forbidden",
    message="Apenas administradores podem criar regras de achievement.",
    status_code=403,
)


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class AchievementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Achievement]:
        statement = (
            select(Achievement)
            .where(Achievement.deleted_at.is_(None))
            .order_by(Achievement.created_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, achievement_id: UUID) -> Achievement | None:
        statement = select(Achievement).where(
            Achievement.id == achievement_id, Achievement.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        description: str,
        icon: str,
        metric: AchievementMetric,
        threshold: int,
    ) -> Achievement:
        achievement = Achievement(
            name=name, description=description, icon=icon, metric=metric, threshold=threshold
        )
        self._session.add(achievement)
        await self._session.flush()
        return achievement


class UserAchievementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: UUID) -> list[UserAchievement]:
        statement = (
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id, UserAchievement.deleted_at.is_(None))
            .order_by(UserAchievement.achieved_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_granted_achievement_ids(self, user_id: UUID) -> set[UUID]:
        statement = select(UserAchievement.achievement_id).where(
            UserAchievement.user_id == user_id, UserAchievement.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return set(result.scalars().all())

    async def create(self, *, user_id: UUID, achievement_id: UUID) -> UserAchievement:
        user_achievement = UserAchievement(
            user_id=user_id, achievement_id=achievement_id, achieved_at=datetime.now(UTC)
        )
        self._session.add(user_achievement)
        await self._session.flush()
        # `achievement` é `lazy="joined"`, mas isso só se aplica a queries feitas via
        # `select()` — um objeto recém-criado por `add()+flush()` não tem a relação
        # carregada. Sem este refresh explícito, acessar `user_achievement.achievement`
        # fora de um contexto já resolvido lançaria `MissingGreenlet`, porque o
        # SQLAlchemy tentaria um lazy-load síncrono implícito em código assíncrono.
        await self._session.refresh(user_achievement, attribute_names=["achievement"])
        return user_achievement


class UserMetricsRepository:
    """Calcula, a partir das tabelas reais, as métricas de progresso de um usuário.

    Isolado do resto do repository para deixar claro que estas são leituras
    somente-agregação, sem nenhuma regra de negócio embutida — a interpretação
    das métricas (o que cada uma significa para conceder um achievement) fica
    inteira no `AchievementService`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_total_xp(self, user_id: UUID) -> int:
        statement = select(func.coalesce(func.sum(XpLedger.amount), 0)).where(
            XpLedger.user_id == user_id
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_lessons_completed_count(self, user_id: UUID) -> int:
        statement = select(func.count(UserLessonProgress.id)).where(
            UserLessonProgress.user_id == user_id, UserLessonProgress.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_badges_count(self, user_id: UUID) -> int:
        statement = select(func.count(UserBadge.id)).where(
            UserBadge.user_id == user_id, UserBadge.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_certificates_count(self, user_id: UUID) -> int:
        statement = select(func.count(UserCertificate.id)).where(
            UserCertificate.user_id == user_id, UserCertificate.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_activity_dates(self, user_id: UUID) -> list[date]:
        """Datas (sem hora) em que o usuário teve pelo menos um lançamento de XP.

        Base para o cálculo de streak — reimplementado localmente no service,
        já que não existe hoje nenhuma tabela dedicada de streak no projeto.
        """

        statement = (
            select(func.date(XpLedger.created_at))
            .where(XpLedger.user_id == user_id)
            .distinct()
            .order_by(func.date(XpLedger.created_at).desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


def _calculate_streak_days(activity_dates: list[date], *, today: date) -> int:
    """Conta dias consecutivos com pelo menos um `XpLedger`, a partir de hoje.

    `activity_dates` já vem ordenado de forma decrescente (mais recente
    primeiro, uma entrada por dia distinto). Sem tolerância: se o usuário não
    tem atividade hoje, o streak é 0 mesmo que tenha estudado ontem — mesma
    semântica de `DashboardService._calculate_streak`
    (`app/domains/dashboard/service.py`), reimplementada aqui localmente
    porque este domínio não depende do domínio `dashboard`.
    """

    if not activity_dates or activity_dates[0] != today:
        return 0

    streak = 0
    expected_date = today
    for activity_date in activity_dates:
        if activity_date != expected_date:
            break
        streak += 1
        expected_date = expected_date.fromordinal(expected_date.toordinal() - 1)

    return streak


class AchievementService:
    def __init__(
        self,
        achievements: AchievementRepository,
        user_achievements: UserAchievementRepository,
        metrics: UserMetricsRepository,
    ) -> None:
        self._achievements = achievements
        self._user_achievements = user_achievements
        self._metrics = metrics

    async def list_catalog(self) -> list[Achievement]:
        return await self._achievements.list_all()

    async def create_rule(
        self,
        *,
        name: str,
        description: str,
        icon: str,
        metric: AchievementMetric,
        threshold: int,
    ) -> Achievement:
        return await self._achievements.create(
            name=name, description=description, icon=icon, metric=metric, threshold=threshold
        )

    async def _current_metric_values(self, user_id: UUID) -> dict[AchievementMetric, int]:
        activity_dates = await self._metrics.get_activity_dates(user_id)
        return {
            AchievementMetric.TOTAL_XP: await self._metrics.get_total_xp(user_id),
            AchievementMetric.LESSONS_COMPLETED: await self._metrics.get_lessons_completed_count(
                user_id
            ),
            AchievementMetric.BADGES_COUNT: await self._metrics.get_badges_count(user_id),
            AchievementMetric.CERTIFICATES_COUNT: await self._metrics.get_certificates_count(
                user_id
            ),
            AchievementMetric.STREAK_DAYS: _calculate_streak_days(
                activity_dates, today=datetime.now(UTC).date()
            ),
        }

    async def evaluate_and_grant(self, user_id: UUID) -> None:
        """Concede qualquer achievement do catálogo cujo threshold já foi atingido
        e que o usuário ainda não possui. Idempotente: chamar repetidamente não
        gera duplicidade (respeitada pela unicidade de `(user_id, achievement_id)`
        e pela checagem prévia contra os já concedidos)."""

        catalog = await self._achievements.list_all()
        if not catalog:
            return

        already_granted = await self._user_achievements.get_granted_achievement_ids(user_id)
        metric_values = await self._current_metric_values(user_id)

        for achievement in catalog:
            if achievement.id in already_granted:
                continue
            if metric_values[achievement.metric] >= achievement.threshold:
                await self._user_achievements.create(
                    user_id=user_id, achievement_id=achievement.id
                )

    async def list_for_user(self, user_id: UUID) -> list[UserAchievement]:
        return await self._user_achievements.list_for_user(user_id)


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
#
# Registrado à parte do router principal de gamification (app/domains/gamification/
# router.py), tocado em paralelo por outras tarefas — este router é incluído
# diretamente em app/api/v1/router.py com o mesmo prefixo "/gamification" para
# expor os endpoints sob o mesmo namespace de API sem editar arquivos concorrentes.

achievements_router = APIRouter(prefix="/gamification", tags=["gamification", "achievements"])


def get_achievement_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AchievementService:
    return AchievementService(
        AchievementRepository(session),
        UserAchievementRepository(session),
        UserMetricsRepository(session),
    )


@achievements_router.get("/achievements")
async def list_achievement_catalog(
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
    achievement_service: Annotated[AchievementService, Depends(get_achievement_service)],
) -> SuccessResponse[list[AchievementResponse]]:
    achievements = await achievement_service.list_catalog()
    data = [AchievementResponse.model_validate(achievement) for achievement in achievements]
    return success_response(request, "Catálogo de achievements recuperado com sucesso.", data)


@achievements_router.get("/me/achievements")
async def list_my_achievements(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    achievement_service: Annotated[AchievementService, Depends(get_achievement_service)],
) -> SuccessResponse[list[UserAchievementResponse]]:
    await achievement_service.evaluate_and_grant(current_user.id)
    user_achievements = await achievement_service.list_for_user(current_user.id)
    data = [
        UserAchievementResponse.model_validate(user_achievement)
        for user_achievement in user_achievements
    ]
    return success_response(request, "Achievements do usuário recuperados com sucesso.", data)


@achievements_router.post("/achievements")
async def create_achievement(
    request: Request,
    payload: CreateAchievementRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    achievement_service: Annotated[AchievementService, Depends(get_achievement_service)],
) -> SuccessResponse[AchievementResponse]:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN

    achievement = await achievement_service.create_rule(
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        metric=payload.metric,
        threshold=payload.threshold,
    )
    data = AchievementResponse.model_validate(achievement)
    return success_response(request, "Regra de achievement criada com sucesso.", data)
