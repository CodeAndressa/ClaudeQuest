"""Ligas (GAME-007).

Reúne, num único arquivo, model + repository + service + schemas + router das
Ligas - mesma decisão deliberada já tomada em `badges.py` e `certificates.py`:
minimizar conflito de merge com outras tarefas em andamento em paralelo na
mesma pasta (Missões Diárias/Semanais e Eventos, cada uma em seu próprio
arquivo novo).

Fonte de verdade da regra de negócio: Vault do Obsidian,
`G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\Ligas e Rankings.md.md`
(seção "Ligas").

Resumo das regras implementadas:

- Sete ligas, em ordem: Bronze, Prata, Ouro, Platina, Diamante, Master, Legend.
- Todo usuário novo entra em Bronze.
- Usuários da mesma liga competem em grupos de até 30, formados por ordem de
  entrada na liga.
- A cada corte semanal (ISO year/week): Top 5 do grupo sobe (Legend não sobe),
  últimos 5 descem (Bronze não desce), demais mantêm.
- Usuário 14+ dias consecutivos sem completar nenhuma missão é excluído do
  cálculo de promoção/rebaixamento daquela semana (não sobe nem desce).
- Desempate: mesmo critério do Ranking Global (`app.domains.gamification.
  ranking`) - menor `user_id` primeiro.

Duas decisões de design deliberadas, documentadas aqui e no relatório final da
tarefa:

1. **Processamento preguiçoso (lazy), sem job agendado.** Não existe nenhum
   scheduler no projeto (sem cron, sem Celery, sem APScheduler) - o mesmo
   padrão já usado para streak e ranking (`app.domains.dashboard.repository`),
   calculados em runtime a partir de dados existentes. Aqui, cada vez que
   `GET /gamification/me/league` é chamado, o backend compara a semana ISO
   corrente (`datetime.now(UTC).isocalendar()`) com `last_processed_iso_week`
   do usuário; se forem diferentes, aplica a promoção/rebaixamento pendente
   *daquele usuário* antes de responder. Efeito colateral aceito: como o
   corte é acionado por usuário (não por um job único que fecha o grupo
   inteiro de uma vez), o grupo pode ficar temporariamente com membros em
   "semanas processadas" diferentes até que cada um chame o endpoint pelo
   menos uma vez após a virada da semana - trade-off aceitável na ausência de
   um scheduler, e sem impacto de correção: cada usuário sempre é avaliado
   contra o ranking do grupo vigente no momento em que sua própria virada de
   semana é detectada.
2. **Sem concessão automática de badge de liga.** A documentação sugere que
   subir de liga concede um badge (ex. "Ouro - Temporada 1"). Como o catálogo
   de badges (`app.domains.gamification.badges`) não tem, nesta entrega,
   nenhuma entrada semeada especificamente para promoções de liga, e a tarefa
   marca essa concessão como opcional/não obrigatória, este módulo não
   concede badge nenhum ao promover - apenas registra a mudança de liga. Fica
   para uma entrega futura, quando o catálogo de badges de liga existir.
"""

import enum
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func, select
from sqlalchemy import Uuid as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditedModel
from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.gamification.ranking import RankingEntry, RankingRepository
from app.domains.learning.model import UserLessonProgress
from app.domains.users.model import User
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

# --------------------------------------------------------------------------- #
# Constantes de regra de negócio
# --------------------------------------------------------------------------- #
#
# Ver docstring do módulo / Vault ("Ligas e Rankings.md.md") para o racional
# de cada valor - todos vêm diretamente do documento, não são estimativas.

GROUP_SIZE = 30
PROMOTION_COUNT = 5
DEMOTION_COUNT = 5
INACTIVITY_DAYS = 14


class League(enum.StrEnum):
    """As sete ligas, na ordem crescente definida pela documentação."""

    BRONZE = "bronze"
    PRATA = "prata"
    OURO = "ouro"
    PLATINA = "platina"
    DIAMANTE = "diamante"
    MASTER = "master"
    LEGEND = "legend"


# Ordem crescente das ligas - usada para determinar a próxima/anterior liga na
# promoção/rebaixamento. Não é a ordem de declaração do enum (que o Python já
# preserva), mas uma constante explícita para deixar a regra auditável sem
# depender de detalhe de implementação do enum.
LEAGUE_ORDER: tuple[League, ...] = (
    League.BRONZE,
    League.PRATA,
    League.OURO,
    League.PLATINA,
    League.DIAMANTE,
    League.MASTER,
    League.LEGEND,
)


def next_league(league: League) -> League:
    """Liga imediatamente acima. Retorna a própria Legend se já for a mais alta."""

    index = LEAGUE_ORDER.index(league)
    return LEAGUE_ORDER[min(index + 1, len(LEAGUE_ORDER) - 1)]


def previous_league(league: League) -> League:
    """Liga imediatamente abaixo. Retorna a própria Bronze se já for a mais baixa."""

    index = LEAGUE_ORDER.index(league)
    return LEAGUE_ORDER[max(index - 1, 0)]


def determine_new_league(*, position: int, total: int, league: League) -> League:
    """Aplica a regra de corte semanal a uma posição (0-based) dentro do grupo.

    Função pura - recebe apenas a posição já ordenada e o tamanho do grupo
    ativo (usuários congelados por inatividade já removidos por quem chama),
    não faz I/O. `position < PROMOTION_COUNT` é checado antes do
    rebaixamento de propósito: num grupo com 5 membros ou menos, todos
    ocupam simultaneamente o "Top 5" e os "últimos 5" - a promoção tem
    prioridade, para não deixar o único/poucos competidores presos numa
    liga por um empate estrutural entre as duas regras.
    """

    if position < PROMOTION_COUNT and league != League.LEGEND:
        return next_league(league)
    if position >= total - DEMOTION_COUNT and league != League.BRONZE:
        return previous_league(league)
    return league


def is_inactive(
    *, entered_league_at: datetime, last_activity_at: datetime | None, now: datetime
) -> bool:
    """Verdadeiro se o usuário está há `INACTIVITY_DAYS`+ dias sem completar missão.

    Quando o usuário nunca completou nenhuma missão (`last_activity_at is
    None`), a referência é `entered_league_at` - um usuário recém-entrado não
    é considerado inativo apenas por ainda não ter concluído nada no mesmo
    instante em que entrou.
    """

    reference = last_activity_at or entered_league_at
    return (now - reference) >= timedelta(days=INACTIVITY_DAYS)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


class UserLeague(AuditedModel):
    """Liga atual de um usuário - cada usuário tem, no máximo, um registro ativo.

    `group_number` identifica o grupo (até `GROUP_SIZE` usuários) dentro da
    liga atual; grupos são formados por ordem de entrada (`entered_league_at`,
    com `user_id` como desempate estável) - ver `LeagueRepository.
    find_available_group`. `last_processed_iso_year`/`last_processed_iso_week`
    guardam a última semana ISO (`datetime.isocalendar()`) para a qual a
    promoção/rebaixamento deste usuário já foi calculada - ver docstring do
    módulo sobre o processamento preguiçoso.

    Não há coluna própria de "última atividade": ela é derivada, sob demanda,
    de `UserLessonProgress.completed_at` (ver `LeagueRepository.
    get_last_activity_map`) - a mesma fonte que já registra conclusão de
    missão em `app.domains.learning`, evitando manter dois lugares
    sincronizados para o mesmo fato.
    """

    __tablename__ = "user_leagues"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_leagues_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    league: Mapped[League] = mapped_column(
        Enum(
            League,
            name="league",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=League.BRONZE,
    )
    group_number: Mapped[int] = mapped_column(nullable=False)
    entered_league_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_processed_iso_year: Mapped[int] = mapped_column(nullable=False)
    last_processed_iso_week: Mapped[int] = mapped_column(nullable=False)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class LeagueGroupMember(BaseModel):
    """Uma linha do ranking do grupo (liga + grupo) do usuário autenticado."""

    user_id: UUID
    name: str
    score: int
    position: int
    is_current_user: bool


class MyLeagueResponse(BaseModel):
    """Liga/grupo atuais do usuário autenticado, com o ranking do grupo."""

    league: League
    group_number: int
    entered_league_at: datetime
    members: list[LeagueGroupMember]


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class LeagueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user(self, user_id: UUID) -> UserLeague | None:
        statement = select(UserLeague).where(
            UserLeague.user_id == user_id, UserLeague.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        league: League,
        group_number: int,
        entered_league_at: datetime,
        last_processed_iso_year: int,
        last_processed_iso_week: int,
    ) -> UserLeague:
        user_league = UserLeague(
            user_id=user_id,
            league=league,
            group_number=group_number,
            entered_league_at=entered_league_at,
            last_processed_iso_year=last_processed_iso_year,
            last_processed_iso_week=last_processed_iso_week,
        )
        self._session.add(user_league)
        await self._session.flush()
        return user_league

    async def find_available_group(self, league: League) -> int:
        """Primeiro número de grupo da liga com menos de `GROUP_SIZE` membros.

        Se nenhum grupo existir ainda para a liga, retorna 1. Se todos os
        grupos existentes já estiverem cheios, retorna o próximo número
        (`max(group_number) + 1`), abrindo um novo grupo.
        """

        statement = (
            select(UserLeague.group_number, func.count().label("member_count"))
            .where(UserLeague.league == league, UserLeague.deleted_at.is_(None))
            .group_by(UserLeague.group_number)
            .order_by(UserLeague.group_number)
        )
        result = await self._session.execute(statement)
        rows = result.all()

        for row in rows:
            if row.member_count < GROUP_SIZE:
                return int(row.group_number)

        return int(rows[-1].group_number) + 1 if rows else 1

    async def list_group_members(self, *, league: League, group_number: int) -> list[UserLeague]:
        statement = (
            select(UserLeague)
            .where(
                UserLeague.league == league,
                UserLeague.group_number == group_number,
                UserLeague.deleted_at.is_(None),
            )
            .order_by(UserLeague.entered_league_at, UserLeague.user_id)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_last_activity_map(self, user_ids: Sequence[UUID]) -> dict[UUID, datetime | None]:
        """Data/hora da última missão concluída por usuário, entre os IDs informados.

        Usuários sem nenhuma linha em `UserLessonProgress` simplesmente não
        aparecem no dicionário retornado - quem chama trata a ausência como
        `None` (ver `is_inactive`).
        """

        if not user_ids:
            return {}

        statement = (
            select(
                UserLessonProgress.user_id,
                func.max(UserLessonProgress.completed_at).label("last_activity"),
            )
            .where(
                UserLessonProgress.user_id.in_(user_ids),
                UserLessonProgress.deleted_at.is_(None),
            )
            .group_by(UserLessonProgress.user_id)
        )
        result = await self._session.execute(statement)
        return {row.user_id: row.last_activity for row in result.all()}

    async def mark_week_processed(
        self, user_league: UserLeague, *, iso_year: int, iso_week: int
    ) -> UserLeague:
        """Atualiza a semana processada sem mover o usuário de liga/grupo."""

        user_league.last_processed_iso_year = iso_year
        user_league.last_processed_iso_week = iso_week
        await self._session.flush()
        return user_league

    async def move_to_league(
        self,
        user_league: UserLeague,
        *,
        league: League,
        group_number: int,
        entered_league_at: datetime,
        iso_year: int,
        iso_week: int,
    ) -> UserLeague:
        """Move o usuário para uma nova liga/grupo (promoção ou rebaixamento)."""

        user_league.league = league
        user_league.group_number = group_number
        user_league.entered_league_at = entered_league_at
        user_league.last_processed_iso_year = iso_year
        user_league.last_processed_iso_week = iso_week
        await self._session.flush()
        return user_league


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class LeagueService:
    """Orquestra o processamento preguiçoso de corte semanal e a leitura de liga.

    Recebe `RankingRepository` (de `app.domains.gamification.ranking`) em vez
    de recalcular pontuação: a regra de desempate/pontuação do corte de liga é
    explicitamente "o mesmo critério do Ranking Global" (Vault, seção
    "Promoção e rebaixamento") - reusar a mesma fonte garante que as duas
    telas nunca divirjam sobre o score de um usuário.
    """

    def __init__(self, leagues: LeagueRepository, ranking: RankingRepository) -> None:
        self._leagues = leagues
        self._ranking = ranking

    async def get_my_league(self, user_id: UUID) -> MyLeagueResponse:
        user_league = await self._get_or_create_user_league(user_id)
        entries_by_id = {entry.user_id: entry for entry in await self._ranking.get_all_entries()}

        user_league = await self._process_pending_week(user_league, entries_by_id)

        return await self._build_group_view(user_league, entries_by_id)

    async def _get_or_create_user_league(self, user_id: UUID) -> UserLeague:
        existing = await self._leagues.get_for_user(user_id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        iso = now.isocalendar()
        group_number = await self._leagues.find_available_group(League.BRONZE)
        return await self._leagues.create(
            user_id=user_id,
            league=League.BRONZE,
            group_number=group_number,
            entered_league_at=now,
            last_processed_iso_year=iso.year,
            last_processed_iso_week=iso.week,
        )

    async def _process_pending_week(
        self, user_league: UserLeague, entries_by_id: dict[UUID, RankingEntry]
    ) -> UserLeague:
        now = datetime.now(UTC)
        iso = now.isocalendar()
        if (iso.year, iso.week) == (
            user_league.last_processed_iso_year,
            user_league.last_processed_iso_week,
        ):
            return user_league

        members = await self._leagues.list_group_members(
            league=user_league.league, group_number=user_league.group_number
        )
        last_activity_map = await self._leagues.get_last_activity_map(
            [member.user_id for member in members]
        )

        if is_inactive(
            entered_league_at=user_league.entered_league_at,
            last_activity_at=last_activity_map.get(user_league.user_id),
            now=now,
        ):
            # Congelado: não sobe nem desce, mas marca a semana como processada
            # para não reavaliar novamente até a próxima virada de semana.
            return await self._leagues.mark_week_processed(
                user_league, iso_year=iso.year, iso_week=iso.week
            )

        active_entries = [
            entries_by_id[member.user_id]
            for member in members
            if member.user_id in entries_by_id
            and not is_inactive(
                entered_league_at=member.entered_league_at,
                last_activity_at=last_activity_map.get(member.user_id),
                now=now,
            )
        ]
        ranked = sorted(active_entries, key=lambda entry: (-entry.score, entry.user_id))
        position = next(
            index for index, entry in enumerate(ranked) if entry.user_id == user_league.user_id
        )

        new_league = determine_new_league(
            position=position, total=len(ranked), league=user_league.league
        )
        if new_league == user_league.league:
            return await self._leagues.mark_week_processed(
                user_league, iso_year=iso.year, iso_week=iso.week
            )

        new_group_number = await self._leagues.find_available_group(new_league)
        return await self._leagues.move_to_league(
            user_league,
            league=new_league,
            group_number=new_group_number,
            entered_league_at=now,
            iso_year=iso.year,
            iso_week=iso.week,
        )

    async def _build_group_view(
        self, user_league: UserLeague, entries_by_id: dict[UUID, RankingEntry]
    ) -> MyLeagueResponse:
        members = await self._leagues.list_group_members(
            league=user_league.league, group_number=user_league.group_number
        )
        ranked = sorted(
            (
                entries_by_id[member.user_id]
                for member in members
                if member.user_id in entries_by_id
            ),
            key=lambda entry: (-entry.score, entry.user_id),
        )

        group_members = [
            LeagueGroupMember(
                user_id=entry.user_id,
                name=entry.name,
                score=entry.score,
                position=position,
                is_current_user=(entry.user_id == user_league.user_id),
            )
            for position, entry in enumerate(ranked, start=1)
        ]

        return MyLeagueResponse(
            league=user_league.league,
            group_number=user_league.group_number,
            entered_league_at=user_league.entered_league_at,
            members=group_members,
        )


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
#
# Registrado à parte do router principal de gamification, mesmo padrão de
# `badges.py`/`certificates.py`: este router é incluído em
# `app/api/v1/router.py` centralmente, depois, para não conflitar com as
# outras tarefas em andamento em paralelo no mesmo diretório.

leagues_router = APIRouter(prefix="/gamification", tags=["gamification", "leagues"])


def get_league_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LeagueService:
    return LeagueService(LeagueRepository(session), RankingRepository(session))


@leagues_router.get("/me/league")
async def get_my_league(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    league_service: Annotated[LeagueService, Depends(get_league_service)],
) -> SuccessResponse[MyLeagueResponse]:
    result = await league_service.get_my_league(current_user.id)
    return success_response(request, "Liga do usuário recuperada com sucesso.", result)
