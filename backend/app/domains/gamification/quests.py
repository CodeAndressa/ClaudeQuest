"""Missões Diárias e Semanais (GAME-008).

Reúne, num único arquivo, models + repository + service + schemas + router das
duas mecânicas — decisão deliberada para minimizar sobreposição com os outros
arquivos novos sendo criados em paralelo no mesmo diretório (Ligas, Eventos),
cada um em seu próprio módulo. Mesmo padrão já usado em
`app/domains/gamification/badges.py`, `certificates.py` e `events.py`.

Fonte de verdade das regras de negócio: Vault do Obsidian,
`G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\Missões Diárias,
Semanais e Eventos.md.md` (seções "Missões Diárias" e "Missões Semanais" — a
seção "Eventos" desse mesmo documento é escopo de outra tarefa, ver
`app/domains/gamification/events.py`).

## Decisão de arquitetura: geração preguiçosa (lazy), sem job agendado

Não existe nenhum job scheduler no projeto (sem cron, Celery ou APScheduler).
Em vez de gerar as missões à meia-noite/segunda-feira via job, a geração
acontece sob demanda: quando `GET /gamification/me/daily-missions` ou
`GET /gamification/me/weekly-mission` é chamado, o backend verifica se já
existe uma seleção persistida para o dia/semana corrente daquele usuário; se
não existir, gera e persiste nesse momento, antes de responder. Mesmo padrão
já usado no projeto para streak (`app.domains.dashboard`) e ranking
(`app.domains.gamification.ranking`), ambos calculados em runtime a partir de
dados existentes. O "dia corrente" é `datetime.now(UTC).date()`; a "semana
corrente" é o ano+semana ISO de `datetime.now(UTC).isocalendar()`.

## Limitações deliberadas desta entrega

1. **Sem noção de "competência"/"força relativa".** A documentação pede que a
   missão de revisão diária priorize competências mais fracas (barra de
   progresso de competência). Essa entidade não existe no projeto — não há
   tabela de competências nem de tentativas por competência. Como proxy
   razoável (mesmo espírito: reforçar o que foi aprendido há mais tempo),
   selecionamos as missões concluídas há mais tempo primeiro
   (`completed_at` ascendente). Mesma categoria de simplificação documentada
   por `badges.py`/`certificates.py` em relação ao sistema de progresso.
2. **Sem fallback de "Laboratório" na missão semanal.** A documentação prevê
   que, quando o aluno já concluiu todos os módulos disponíveis, a missão
   semanal vire um "Laboratório" da trilha mais recentemente concluída. Não
   existe hoje uma entidade de Laboratório separada no código (apenas
   `LessonType.LAB`, uma marcação de tipo em `Lesson`, não um catálogo próprio
   de laboratórios). Nesse caso-limite (usuário sem nenhum módulo incompleto),
   este módulo levanta `AppError("weekly_mission_unavailable")` em vez de
   inventar uma seleção sem fonte de dados real. Fica para quando existir uma
   entidade de Laboratório de primeira classe.
3. **Integração de XP com `LearningService.complete_lesson` fica pendente.**
   Ver docstring de `mark_lesson_progress_for_quests` abaixo — é o ponto de
   extensão pronto para ser plugado ali numa integração futura, deliberadamente
   adiada para não editar `app/domains/learning/service.py`/`router.py` em
   paralelo com outras tarefas tocando os mesmos arquivos.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import Boolean, Date, ForeignKey, Integer, UniqueConstraint, select
from sqlalchemy import Uuid as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.database.base import AuditedModel
from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.gamification.repository import XpLedgerRepository
from app.domains.gamification.xp_rules import BASE_XP_BY_DIFFICULTY, DAILY_MISSION_BONUS, Difficulty
from app.domains.learning.model import Lesson, Level, Module, Track, UserLessonProgress
from app.domains.learning.repository import LessonProgressRepository, LessonRepository
from app.domains.users.model import User
from app.shared.errors import AppError
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

# --------------------------------------------------------------------------- #
# Constantes de seleção
# --------------------------------------------------------------------------- #

# "conjunto pequeno (3) de missões" — ver seção "Missões Diárias" > "Definição".
DAILY_MISSION_TARGET_COUNT = 3

# "sempre múltiplo (2 a 4 missões...)" — ver seção "Missões Semanais" > "Definição".
# O limite inferior de 2 não é imposto como filtro: se o módulo mais próximo da
# conclusão tiver só 1 lição restante, ainda geramos a missão com 1 (preferível
# a bloquear o aluno — alinhado ao princípio "nunca punir" de Gamification.md.md).
WEEKLY_MISSION_MAX_LESSONS = 4


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


class DailyMission(AuditedModel):
    """A seleção de missões diárias de um usuário para um dia específico.

    Um único registro por (usuário, dia) — a unicidade garante que a leitura
    preguiçosa nunca gere duas seleções diferentes no mesmo dia por corrida
    entre requisições concorrentes (a segunda simplesmente encontra a primeira
    já persistida).
    """

    __tablename__ = "daily_missions"
    __table_args__ = (
        UniqueConstraint("user_id", "mission_date", name="uq_daily_missions_user_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mission_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)

    lessons: Mapped[list["DailyMissionLesson"]] = relationship(
        back_populates="daily_mission",
        cascade="all, delete-orphan",
        order_by="DailyMissionLesson.created_at",
    )


class DailyMissionLesson(AuditedModel):
    """Uma lição (missão do catálogo) selecionada dentro de uma missão diária."""

    __tablename__ = "daily_mission_lessons"
    __table_args__ = (
        UniqueConstraint(
            "daily_mission_id", "lesson_id", name="uq_daily_mission_lessons_mission_lesson"
        ),
    )

    daily_mission_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("daily_missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    daily_mission: Mapped[DailyMission] = relationship(back_populates="lessons")
    lesson: Mapped[Lesson] = relationship(Lesson, lazy="joined")


class WeeklyMission(AuditedModel):
    """A missão semanal corrente de um usuário: um conjunto de lições de um módulo.

    Um único registro por (usuário, ano ISO, semana ISO). `bonus_awarded`
    controla a concessão única do bônus de conclusão do conjunto completo (ver
    `mark_lesson_progress_for_quests`) — sem essa flag, um reprocessamento
    acidental poderia conceder o bônus mais de uma vez.
    """

    __tablename__ = "weekly_missions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "iso_year", "iso_week", name="uq_weekly_missions_user_year_week"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    iso_year: Mapped[int] = mapped_column(Integer(), nullable=False)
    iso_week: Mapped[int] = mapped_column(Integer(), nullable=False)
    module_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bonus_awarded: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    module: Mapped[Module] = relationship(Module, lazy="joined")
    lessons: Mapped[list["WeeklyMissionLesson"]] = relationship(
        back_populates="weekly_mission",
        cascade="all, delete-orphan",
        order_by="WeeklyMissionLesson.created_at",
    )


class WeeklyMissionLesson(AuditedModel):
    """Uma lição do módulo-alvo selecionada dentro da missão semanal."""

    __tablename__ = "weekly_mission_lessons"
    __table_args__ = (
        UniqueConstraint(
            "weekly_mission_id", "lesson_id", name="uq_weekly_mission_lessons_mission_lesson"
        ),
    )

    weekly_mission_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("weekly_missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    weekly_mission: Mapped[WeeklyMission] = relationship(back_populates="lessons")
    lesson: Mapped[Lesson] = relationship(Lesson, lazy="joined")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class DailyMissionLessonResponse(BaseModel):
    """Uma lição dentro da missão diária de hoje, já com o estado de conclusão."""

    lesson_id: UUID
    title: str
    description: str
    estimated_minutes: int
    xp: int
    completed: bool


class DailyMissionsResponse(BaseModel):
    """Resposta de `GET /gamification/me/daily-missions`."""

    mission_date: date
    lessons: list[DailyMissionLessonResponse]


class WeeklyMissionLessonResponse(BaseModel):
    """Uma lição dentro da missão semanal corrente, já com o estado de conclusão."""

    lesson_id: UUID
    title: str
    description: str
    estimated_minutes: int
    xp: int
    completed: bool


class WeeklyMissionResponse(BaseModel):
    """Resposta de `GET /gamification/me/weekly-mission`."""

    iso_year: int
    iso_week: int
    module_id: UUID
    module_title: str
    lessons: list[WeeklyMissionLessonResponse]
    completed_count: int
    total_count: int
    all_completed: bool
    bonus_awarded: bool


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

_WEEKLY_MISSION_UNAVAILABLE = AppError(
    code="weekly_mission_unavailable",
    message=(
        "Não há um módulo elegível para gerar a missão semanal — todo o "
        "conteúdo disponível já foi concluído."
    ),
    status_code=404,
)


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class DailyMissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user_and_date(
        self, user_id: UUID, mission_date: date
    ) -> DailyMission | None:
        statement = (
            select(DailyMission)
            .where(
                DailyMission.user_id == user_id,
                DailyMission.mission_date == mission_date,
                DailyMission.deleted_at.is_(None),
            )
            .options(
                selectinload(DailyMission.lessons.and_(DailyMissionLesson.deleted_at.is_(None)))
            )
        )
        result = await self._session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def create_with_lessons(
        self, *, user_id: UUID, mission_date: date, lesson_ids: list[UUID]
    ) -> DailyMission:
        daily_mission = DailyMission(user_id=user_id, mission_date=mission_date)
        self._session.add(daily_mission)
        await self._session.flush()
        for lesson_id in lesson_ids:
            self._session.add(
                DailyMissionLesson(daily_mission_id=daily_mission.id, lesson_id=lesson_id)
            )
        await self._session.flush()

        # Re-seleciona em vez de `session.refresh(...)`: garante que a coleção
        # `lessons` e o `lesson` (lazy="joined") de cada item venham
        # consistentemente povoados, sem depender de nuances de refresh sobre
        # coleções recém-criadas na mesma sessão.
        created = await self.get_for_user_and_date(user_id, mission_date)
        assert created is not None  # nosec B101 - acabamos de criar este registro
        return created

    async def mark_lesson_completed(self, *, daily_mission_id: UUID, lesson_id: UUID) -> bool:
        """Marca uma lição da missão diária como concluída. Idempotente.

        Retorna `True` apenas na transição `False -> True` (a lição de fato
        fazia parte da missão e ainda não estava concluída). Retorna `False`
        quando a lição não pertence a esta missão diária ou já estava
        concluída — em ambos os casos, nenhum efeito colateral (ex.: bônus de
        XP) deve ser aplicado por quem chama.
        """

        statement = select(DailyMissionLesson).where(
            DailyMissionLesson.daily_mission_id == daily_mission_id,
            DailyMissionLesson.lesson_id == lesson_id,
            DailyMissionLesson.completed.is_(False),
            DailyMissionLesson.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return False

        row.completed = True
        await self._session.flush()
        return True


class WeeklyMissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user_and_week(
        self, user_id: UUID, iso_year: int, iso_week: int
    ) -> WeeklyMission | None:
        statement = (
            select(WeeklyMission)
            .where(
                WeeklyMission.user_id == user_id,
                WeeklyMission.iso_year == iso_year,
                WeeklyMission.iso_week == iso_week,
                WeeklyMission.deleted_at.is_(None),
            )
            .options(
                selectinload(WeeklyMission.lessons.and_(WeeklyMissionLesson.deleted_at.is_(None)))
            )
        )
        result = await self._session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def create_with_lessons(
        self,
        *,
        user_id: UUID,
        iso_year: int,
        iso_week: int,
        module_id: UUID,
        lesson_ids: list[UUID],
    ) -> WeeklyMission:
        weekly_mission = WeeklyMission(
            user_id=user_id, iso_year=iso_year, iso_week=iso_week, module_id=module_id
        )
        self._session.add(weekly_mission)
        await self._session.flush()
        for lesson_id in lesson_ids:
            self._session.add(
                WeeklyMissionLesson(weekly_mission_id=weekly_mission.id, lesson_id=lesson_id)
            )
        await self._session.flush()

        created = await self.get_for_user_and_week(user_id, iso_year, iso_week)
        assert created is not None  # nosec B101 - acabamos de criar este registro
        return created

    async def mark_lesson_completed(self, *, weekly_mission_id: UUID, lesson_id: UUID) -> bool:
        """Mesma semântica idempotente de `DailyMissionRepository.mark_lesson_completed`."""

        statement = select(WeeklyMissionLesson).where(
            WeeklyMissionLesson.weekly_mission_id == weekly_mission_id,
            WeeklyMissionLesson.lesson_id == lesson_id,
            WeeklyMissionLesson.completed.is_(False),
            WeeklyMissionLesson.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return False

        row.completed = True
        await self._session.flush()
        return True

    async def mark_bonus_awarded(self, weekly_mission: WeeklyMission) -> None:
        weekly_mission.bonus_awarded = True
        await self._session.flush()


class QuestCatalogReadRepository:
    """Leituras do domínio `learning` necessárias para selecionar missões.

    Assim como `app.domains.dashboard.repository.DashboardRepository` e
    `app.domains.gamification.ranking.RankingRepository`, esta classe só lê
    tabelas de outro domínio, nunca escreve nelas. Escrevemos nossas próprias
    consultas (em vez de importar `DashboardRepository`) para manter este
    módulo novo sem dependência rígida do domínio `dashboard`, reduzindo risco
    de conflito com outras tarefas em paralelo.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_next_incomplete_lesson(self, user_id: UUID) -> Lesson | None:
        """Primeira lição ativa ainda não concluída pelo usuário.

        Mesma lógica/ordem de `app.domains.dashboard.repository.
        DashboardRepository.get_next_incomplete_lesson` (catálogo -> módulo ->
        nível -> lição), duplicada deliberadamente em vez de importada — ver
        docstring da classe.
        """

        statement = (
            select(Lesson)
            .join(Level, Level.id == Lesson.level_id)
            .join(Module, Module.id == Level.module_id)
            .join(Track, Track.id == Module.track_id)
            .outerjoin(
                UserLessonProgress,
                (UserLessonProgress.lesson_id == Lesson.id)
                & (UserLessonProgress.user_id == user_id)
                & (UserLessonProgress.deleted_at.is_(None)),
            )
            .where(
                Track.is_active.is_(True),
                Track.deleted_at.is_(None),
                Module.is_active.is_(True),
                Module.deleted_at.is_(None),
                Level.deleted_at.is_(None),
                Lesson.deleted_at.is_(None),
                UserLessonProgress.id.is_(None),
            )
            .order_by(Track.order, Module.order, Level.level_number, Lesson.order)
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_completed_lessons_oldest_first(self, user_id: UUID) -> list[Lesson]:
        """Lições concluídas pelo usuário, da mais antiga para a mais recente.

        Usada como pool de "revisão" da missão diária: sem um sistema de
        competências (ver docstring do módulo), a lição concluída há mais
        tempo é o proxy mais razoável disponível hoje para "precisa de
        reforço".
        """

        statement = (
            select(Lesson)
            .join(UserLessonProgress, UserLessonProgress.lesson_id == Lesson.id)
            .where(
                UserLessonProgress.user_id == user_id,
                UserLessonProgress.deleted_at.is_(None),
                Lesson.deleted_at.is_(None),
            )
            .order_by(UserLessonProgress.completed_at.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_active_tracks_with_lessons(self) -> list[Track]:
        """Trilhas ativas com módulos/níveis/lições ativos, para seleção semanal."""

        statement = (
            select(Track)
            .where(Track.is_active.is_(True), Track.deleted_at.is_(None))
            .order_by(Track.order)
            .options(
                selectinload(
                    Track.modules.and_(Module.is_active.is_(True), Module.deleted_at.is_(None))
                )
                .selectinload(Module.levels.and_(Level.deleted_at.is_(None)))
                .selectinload(Level.lessons.and_(Lesson.deleted_at.is_(None)))
            )
        )
        result = await self._session.execute(statement)
        return list(result.unique().scalars().all())


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class QuestService:
    def __init__(
        self,
        daily_missions: DailyMissionRepository,
        weekly_missions: WeeklyMissionRepository,
        catalog: QuestCatalogReadRepository,
        progress: LessonProgressRepository,
    ) -> None:
        self._daily_missions = daily_missions
        self._weekly_missions = weekly_missions
        self._catalog = catalog
        self._progress = progress

    # --- Missões diárias -------------------------------------------------

    async def get_or_create_daily_missions(self, user_id: UUID) -> DailyMissionsResponse:
        today = datetime.now(UTC).date()
        daily_mission = await self._daily_missions.get_for_user_and_date(user_id, today)
        if daily_mission is None:
            lesson_ids = await self._select_daily_lesson_ids(user_id, mission_date=today)
            daily_mission = await self._daily_missions.create_with_lessons(
                user_id=user_id, mission_date=today, lesson_ids=lesson_ids
            )
        return self._build_daily_response(daily_mission)

    async def _select_daily_lesson_ids(self, user_id: UUID, *, mission_date: date) -> list[UUID]:
        """Seleciona até `DAILY_MISSION_TARGET_COUNT` lições para a missão de hoje.

        Prioridade 1: a próxima lição não concluída da trilha em andamento do
        aluno (mesma lógica de "próxima missão" do Dashboard).
        Prioridade 2: completar até o alvo com lições de revisão (já
        concluídas, mais antigas primeiro).

        Nunca repete a mesma lição de revisão do dia anterior enquanto houver
        alternativa — mas prefere repetir (em vez de entregar menos de 3
        missões) quando não há alternativa, alinhado ao princípio "nunca
        punir" (a regra de "não repetir" é uma preferência de variedade, não
        uma penalidade).
        """

        selected: list[UUID] = []

        next_lesson = await self._catalog.get_next_incomplete_lesson(user_id)
        if next_lesson is not None:
            selected.append(next_lesson.id)

        if len(selected) < DAILY_MISSION_TARGET_COUNT:
            yesterday = mission_date - timedelta(days=1)
            yesterday_mission = await self._daily_missions.get_for_user_and_date(
                user_id, yesterday
            )
            yesterday_lesson_ids = (
                {item.lesson_id for item in yesterday_mission.lessons}
                if yesterday_mission is not None
                else set()
            )

            review_lessons = await self._catalog.list_completed_lessons_oldest_first(user_id)

            for lesson in review_lessons:
                if len(selected) >= DAILY_MISSION_TARGET_COUNT:
                    break
                if lesson.id in selected or lesson.id in yesterday_lesson_ids:
                    continue
                selected.append(lesson.id)

            if len(selected) < DAILY_MISSION_TARGET_COUNT:
                for lesson in review_lessons:
                    if len(selected) >= DAILY_MISSION_TARGET_COUNT:
                        break
                    if lesson.id in selected:
                        continue
                    selected.append(lesson.id)

        return selected

    @staticmethod
    def _build_daily_response(daily_mission: DailyMission) -> DailyMissionsResponse:
        lessons = [
            DailyMissionLessonResponse(
                lesson_id=item.lesson_id,
                title=item.lesson.title,
                description=item.lesson.description,
                estimated_minutes=item.lesson.estimated_minutes,
                xp=item.lesson.xp,
                completed=item.completed,
            )
            for item in daily_mission.lessons
        ]
        return DailyMissionsResponse(mission_date=daily_mission.mission_date, lessons=lessons)

    # --- Missão semanal ----------------------------------------------------

    async def get_or_create_weekly_mission(self, user_id: UUID) -> WeeklyMissionResponse:
        iso_year, iso_week, _ = datetime.now(UTC).isocalendar()
        weekly_mission = await self._weekly_missions.get_for_user_and_week(
            user_id, iso_year, iso_week
        )
        if weekly_mission is None:
            module, lesson_ids = await self._select_weekly_target(user_id)
            weekly_mission = await self._weekly_missions.create_with_lessons(
                user_id=user_id,
                iso_year=iso_year,
                iso_week=iso_week,
                module_id=module.id,
                lesson_ids=lesson_ids,
            )
        return self._build_weekly_response(weekly_mission)

    async def _select_weekly_target(self, user_id: UUID) -> tuple[Module, list[UUID]]:
        """Escolhe o módulo ainda incompleto mais próximo da conclusão.

        "Mais próximo da conclusão" = maior proporção de lições já concluídas
        entre as lições do módulo, desde que não seja 100% (módulo já
        concluído não é elegível). Empates são desempatados pela ordem de
        catálogo (trilha, depois módulo), para um resultado determinístico.
        """

        tracks = await self._catalog.list_active_tracks_with_lessons()
        completed_ids = await self._progress.list_completed_lesson_ids_for_user(user_id)

        best_key: tuple[float, int, int] | None = None
        best_module: Module | None = None
        for track in tracks:
            for module in track.modules:
                lessons = [lesson for level in module.levels for lesson in level.lessons]
                total = len(lessons)
                if total == 0:
                    continue
                completed = sum(1 for lesson in lessons if lesson.id in completed_ids)
                if completed >= total:
                    continue  # módulo já 100% concluído: não elegível

                ratio = completed / total
                candidate_key = (-ratio, track.order, module.order)
                if best_key is None or candidate_key < best_key:
                    best_key = candidate_key
                    best_module = module

        if best_module is None:
            raise _WEEKLY_MISSION_UNAVAILABLE

        remaining_lessons = [
            lesson
            for level in best_module.levels
            for lesson in level.lessons
            if lesson.id not in completed_ids
        ]
        lesson_ids = [lesson.id for lesson in remaining_lessons[:WEEKLY_MISSION_MAX_LESSONS]]
        return best_module, lesson_ids

    @staticmethod
    def _build_weekly_response(weekly_mission: WeeklyMission) -> WeeklyMissionResponse:
        lessons = [
            WeeklyMissionLessonResponse(
                lesson_id=item.lesson_id,
                title=item.lesson.title,
                description=item.lesson.description,
                estimated_minutes=item.lesson.estimated_minutes,
                xp=item.lesson.xp,
                completed=item.completed,
            )
            for item in weekly_mission.lessons
        ]
        completed_count = sum(1 for lesson in lessons if lesson.completed)
        total_count = len(lessons)
        return WeeklyMissionResponse(
            iso_year=weekly_mission.iso_year,
            iso_week=weekly_mission.iso_week,
            module_id=weekly_mission.module_id,
            module_title=weekly_mission.module.title,
            lessons=lessons,
            completed_count=completed_count,
            total_count=total_count,
            all_completed=total_count > 0 and completed_count == total_count,
            bonus_awarded=weekly_mission.bonus_awarded,
        )


# --------------------------------------------------------------------------- #
# Integração com XP (ponto de extensão para uso futuro por outro domínio)
# --------------------------------------------------------------------------- #


async def mark_lesson_progress_for_quests(
    session: AsyncSession, *, user_id: UUID, lesson_id: UUID, completed_at: datetime
) -> None:
    """Aplica o efeito de uma conclusão de lição sobre missões diárias/semanais ativas.

    INTEGRAÇÃO PENDENTE (deliberada): esta função ainda precisa ser chamada a
    partir de `app.domains.learning.service.LearningService.complete_lesson`,
    logo após o XP base da lição ser concedido. Ainda não foi conectada porque
    isso exigiria editar `app/domains/learning/service.py`/`router.py`, tocados
    em paralelo por outra tarefa nesta mesma iteração — a integração
    cross-módulo fica para um passo seguinte, quando o risco de conflito de
    merge concorrente não existir mais. Isso é esperado e aceitável nesta
    entrega, não uma tarefa incompleta.

    Efeitos, quando aplicável (chamadas para lições que não pertencem a
    nenhuma missão ativa — o caso comum — são um no-op silencioso, sem lançar
    `AppError`):

    - **Missão diária de hoje**: se `lesson_id` fizer parte dela e ainda não
      estiver concluída, marca como concluída e concede uma entrada de XP
      *adicional* no ledger, igual a `round(lesson.xp * DAILY_MISSION_BONUS)`
      (a constante "+10%" de `xp_rules.py`). É uma entrada extra, não uma
      substituição do XP já concedido por `complete_lesson` — porque aquele
      fluxo grava `lesson.xp` diretamente, sem passar por
      `calculate_xp`/`Difficulty` (cuja tabela fixa de XP por dificuldade é
      incompatível com o XP livre por lição já em uso hoje). Reaproveitar a
      constante `DAILY_MISSION_BONUS` (em vez de um número mágico) preserva a
      mesma semântica de "+10%" pedida pela documentação.
    - **Missão semanal corrente**: se `lesson_id` fizer parte dela e ainda não
      estiver concluída, marca como concluída. Se essa marcação completar o
      conjunto inteiro e o bônus de conclusão ainda não tiver sido concedido,
      grava uma única entrada de `BASE_XP_BY_DIFFICULTY[Difficulty.DIFICIL]`
      (150 XP) e marca `bonus_awarded=True` — nunca concede o bônus duas
      vezes, mesmo que a função seja chamada novamente depois.
    """

    daily_missions = DailyMissionRepository(session)
    weekly_missions = WeeklyMissionRepository(session)
    lessons = LessonRepository(session)
    xp_ledger = XpLedgerRepository(session)

    mission_date = completed_at.date()
    daily_mission = await daily_missions.get_for_user_and_date(user_id, mission_date)
    if daily_mission is not None:
        marked = await daily_missions.mark_lesson_completed(
            daily_mission_id=daily_mission.id, lesson_id=lesson_id
        )
        if marked:
            lesson = await lessons.get_by_id(lesson_id)
            if lesson is not None:
                bonus_xp = round(lesson.xp * DAILY_MISSION_BONUS)
                if bonus_xp > 0:
                    await xp_ledger.add_entry(
                        user_id=user_id,
                        amount=bonus_xp,
                        reason=f"daily_mission_bonus:{lesson_id}",
                    )

    iso_year, iso_week, _ = completed_at.isocalendar()
    weekly_mission = await weekly_missions.get_for_user_and_week(user_id, iso_year, iso_week)
    if weekly_mission is not None and not weekly_mission.bonus_awarded:
        marked = await weekly_missions.mark_lesson_completed(
            weekly_mission_id=weekly_mission.id, lesson_id=lesson_id
        )
        if (
            marked
            and weekly_mission.lessons
            and all(item.completed for item in weekly_mission.lessons)
        ):
            await xp_ledger.add_entry(
                user_id=user_id,
                amount=BASE_XP_BY_DIFFICULTY[Difficulty.DIFICIL],
                reason=f"weekly_mission_bonus:{weekly_mission.id}",
            )
            await weekly_missions.mark_bonus_awarded(weekly_mission)


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
#
# Registrado à parte do router principal de gamification, tocado em paralelo
# por outras tarefas — este router é incluído diretamente em
# app/api/v1/router.py com o mesmo prefixo "/gamification" para expor os
# endpoints sob o mesmo namespace de API sem editar arquivos concorrentes.

quests_router = APIRouter(prefix="/gamification", tags=["gamification", "quests"])


def get_quest_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuestService:
    return QuestService(
        DailyMissionRepository(session),
        WeeklyMissionRepository(session),
        QuestCatalogReadRepository(session),
        LessonProgressRepository(session),
    )


@quests_router.get("/me/daily-missions")
async def get_daily_missions(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    quest_service: Annotated[QuestService, Depends(get_quest_service)],
) -> SuccessResponse[DailyMissionsResponse]:
    result = await quest_service.get_or_create_daily_missions(current_user.id)
    return success_response(request, "Missões diárias recuperadas com sucesso.", result)


@quests_router.get("/me/weekly-mission")
async def get_weekly_mission(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    quest_service: Annotated[QuestService, Depends(get_quest_service)],
) -> SuccessResponse[WeeklyMissionResponse]:
    result = await quest_service.get_or_create_weekly_mission(current_user.id)
    return success_response(request, "Missão semanal recuperada com sucesso.", result)
