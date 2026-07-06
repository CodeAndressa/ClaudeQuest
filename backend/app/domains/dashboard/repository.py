from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gamification.model import XpLedger
from app.domains.learning.model import Lesson, Level, Module, Track, UserLessonProgress
from app.domains.users.model import User


class DashboardRepository:
    """Acesso a dados agregados de mÃºltiplos domÃ­nios para o MÃ³dulo Dashboard.

    Fica em seu prÃ³prio domÃ­nio (e nÃ£o dentro de `gamification`/`learning`) porque
    a agregaÃ§Ã£o que ele faz â€” XP + streak + ranking + prÃ³xima missÃ£o â€” nÃ£o Ã© uma
    responsabilidade de nenhum domÃ­nio individual, Ã© a composiÃ§Ã£o de vÃ¡rios. Cada
    consulta aqui sÃ³ lÃª tabelas de outros domÃ­nios (nunca escreve nelas), o que
    respeita a regra de "baixo acoplamento" do MÃ³dulo Dashboard na Functional
    Specification sem duplicar a lÃ³gica de cÃ¡lculo de XP/nÃ­vel, que continua
    vivendo em `app.domains.gamification`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_total_xp(self, user_id: UUID) -> int:
        statement = select(func.coalesce(func.sum(XpLedger.amount), 0)).where(
            XpLedger.user_id == user_id
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_distinct_xp_dates_desc(self, user_id: UUID) -> list[date]:
        """Datas (UTC) distintas em que o usuÃ¡rio recebeu XP, mais recentes primeiro.

        Usada para calcular o streak em memÃ³ria no Service â€” a contagem de dias
        consecutivos envolve lÃ³gica de negÃ³cio (parar no primeiro "buraco"), que
        nÃ£o pertence ao Repository.
        """

        xp_date = func.date(XpLedger.created_at)
        statement = (
            select(xp_date.label("xp_date"))
            .where(XpLedger.user_id == user_id)
            .group_by(xp_date)
            .order_by(xp_date.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_ranking_position(self, user_id: UUID) -> int | None:
        """PosiÃ§Ã£o (1-based) do usuÃ¡rio no ranking global por XP total (desc).

        Empates sÃ£o desempatados por `id` (ordem estÃ¡vel), conforme a regra da
        tarefa. Retorna `None` se o usuÃ¡rio nÃ£o existir mais (ex.: deletado entre
        a autenticaÃ§Ã£o e a consulta) â€” caso defensivo, nÃ£o esperado em uso normal.
        """

        total_xp_subquery = (
            select(
                User.id.label("user_id"),
                func.coalesce(func.sum(XpLedger.amount), 0).label("total_xp"),
            )
            .outerjoin(XpLedger, XpLedger.user_id == User.id)
            .where(User.deleted_at.is_(None))
            .group_by(User.id)
            .subquery()
        )
        rank_column = (
            func.rank()
            .over(order_by=(total_xp_subquery.c.total_xp.desc(), total_xp_subquery.c.user_id.asc()))
            .label("position")
        )
        ranked = select(total_xp_subquery.c.user_id, rank_column).subquery()

        statement = select(ranked.c.position).where(ranked.c.user_id == user_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_total_users(self) -> int:
        statement = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_next_incomplete_lesson(self, user_id: UUID) -> tuple[Track, Lesson] | None:
        """Primeira missao ativa ainda nao concluida pelo usuario.

        A ordem respeita catalogo -> modulo -> nivel -> missao. Quando todas as
        missoes publicadas estiverem concluidas, retorna `None`.
        """

        statement = (
            select(Track, Lesson)
            .join(Module, Module.track_id == Track.id)
            .join(Level, Level.module_id == Module.id)
            .join(Lesson, Lesson.level_id == Level.id)
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
        row = result.first()
        if row is None:
            return None
        return row.Track, row.Lesson
