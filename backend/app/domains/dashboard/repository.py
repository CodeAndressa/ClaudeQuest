from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.gamification.model import XpLedger
from app.domains.learning.model import Lesson, Level, Module, Track
from app.domains.users.model import User


class DashboardRepository:
    """Acesso a dados agregados de múltiplos domínios para o Módulo Dashboard.

    Fica em seu próprio domínio (e não dentro de `gamification`/`learning`) porque
    a agregação que ele faz — XP + streak + ranking + próxima missão — não é uma
    responsabilidade de nenhum domínio individual, é a composição de vários. Cada
    consulta aqui só lê tabelas de outros domínios (nunca escreve nelas), o que
    respeita a regra de "baixo acoplamento" do Módulo Dashboard na Functional
    Specification sem duplicar a lógica de cálculo de XP/nível, que continua
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
        """Datas (UTC) distintas em que o usuário recebeu XP, mais recentes primeiro.

        Usada para calcular o streak em memória no Service — a contagem de dias
        consecutivos envolve lógica de negócio (parar no primeiro "buraco"), que
        não pertence ao Repository.
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
        """Posição (1-based) do usuário no ranking global por XP total (desc).

        Empates são desempatados por `id` (ordem estável), conforme a regra da
        tarefa. Retorna `None` se o usuário não existir mais (ex.: deletado entre
        a autenticação e a consulta) — caso defensivo, não esperado em uso normal.
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

    async def get_first_lesson_of_first_active_track(self) -> tuple[str, Lesson] | None:
        """Primeira missão (por `order`) da primeira trilha ativa (por `order`).

        Aproximação documentada na tarefa: ainda não existe uma tabela de
        progresso do aluno, então "próxima missão" é sempre a primeira missão do
        conteúdo, não a próxima incompleta. Retorna `None` quando não há nenhuma
        trilha ativa com conteúdo completo (trilha -> módulo -> nível -> missão).
        """

        statement = (
            select(Track)
            .where(Track.is_active.is_(True), Track.deleted_at.is_(None))
            .order_by(Track.order)
            .options(
                selectinload(Track.modules.and_(Module.deleted_at.is_(None)))
                .selectinload(Module.levels.and_(Level.deleted_at.is_(None)))
                .selectinload(Level.lessons.and_(Lesson.deleted_at.is_(None)))
            )
        )
        result = await self._session.execute(statement)
        tracks = list(result.unique().scalars().all())

        for track in tracks:
            for module in sorted(track.modules, key=lambda m: m.order):
                for level in sorted(module.levels, key=lambda lv: lv.level_number):
                    lessons = sorted(level.lessons, key=lambda ls: ls.order)
                    if lessons:
                        return track.title, lessons[0]
        return None
