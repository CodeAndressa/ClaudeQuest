"""
Ranking (GAME-004): pontuação combinada de gamificação, além do XP puro.

Fonte de verdade da regra de negócio: Vault do Obsidian,
`G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\Gamification.md.md`,
seção "Rankings" / "Pontuação":

    Ranking utilizará: XP, Projetos, Certificações, Missões concluídas,
    Laboratórios. Nunca apenas XP.

Decisão de design (sujeita a revisão quando houver mais dados disponíveis):
no momento desta implementação **não existe** sistema de progresso que
produza dados reais de "Projetos", "Missões concluídas" nem "Laboratórios"
(não há tabela de progresso do aluno — o próprio Dashboard, ao implementar o
ranking simplificado em GAME-001/dashboard, documentou essa mesma lacuna).
Combinamos apenas o que existe de verdade no banco hoje:

  - XP total do usuário (soma do `xp_ledger`, já usado em todo o domínio
    `gamification`);
  - Badges conquistados (`UserBadge`, de `app.domains.gamification.badges`,
    entregue em paralelo por GAME-002);
  - Certificados emitidos (`UserCertificate`, de
    `app.domains.gamification.certificates`, entregue em paralelo por
    GAME-006).

Fórmula escolhida (pesos arbitrários, não especificados pelo documento de
produto — precisam de validação de negócio quando houver dados reais de
Projetos e Missões para calibrar o peso relativo de cada fonte):

    score = total_xp + (badges_count * 100) + (certificates_count * 500)

Racional dos pesos: um certificado representa a conclusão de uma trilha
inteira (documentação de XP já trata "Certificação" como o evento de maior
valor isolado, 2000 XP) — por isso pesa mais que um badge individual (marco
pontual, ex.: "Primeira Missão"). Os valores 100/500 foram escolhidos para
que badges e certificados movam o ranking de forma perceptível sem dominar
por completo um usuário com XP genuinamente alto; ambos devem ser revistos
assim que "Projetos" e "Missões concluídas" tiverem uma fonte de dados real
a incorporar na fórmula.

Escopo desta entrega: apenas o ranking **Global** (todos os usuários, sem
recorte de tempo). Os demais escopos listados na documentação — Empresa,
Área, Equipe, Turma, Semanal, Mensal, Anual, Histórico — ficam pendentes:
Empresa/Área/Equipe/Turma dependem de uma modelagem de Organization/Team
mais rica do que a que existe hoje (hoje só há `organization_id` em
`User`, sem hierarquia de área/equipe); Semanal/Mensal/Anual dependem de um
recorte temporal de `xp_ledger` por período (hoje a soma é sempre o
acumulado desde o início da conta) e de uma decisão de produto sobre como
"resetar" (ou não) badges/certificados nesses recortes.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import Subquery, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.gamification.model import XpLedger
from app.domains.users.model import User
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

# --- Pesos da fórmula de pontuação --------------------------------------
#
# Ver docstring do módulo para o racional. Nomeados como constantes (em vez
# de números soltos na fórmula) para que a calibração futura seja uma
# alteração de uma linha, não uma caça a "números mágicos".
BADGE_WEIGHT = 100
CERTIFICATE_WEIGHT = 500


def calculate_score(*, total_xp: int, badges_count: int, certificates_count: int) -> int:
    """Calcula o score de ranking de um usuário a partir do que hoje é mensurável.

    Função pura, sem I/O — testável isoladamente e reutilizável por qualquer
    chamador (ex.: um futuro job de recálculo em lote), seguindo o mesmo
    padrão de `app.domains.gamification.xp_rules.calculate_xp`.

    Não valida limites superiores (XP, badges e certificados já nascem
    não-negativos em suas respectivas fontes); valores negativos aqui
    indicariam um bug em quem chama, não um caso de negócio válido — por
    isso a função não lança exceção, apenas soma o que recebe.
    """

    return total_xp + (badges_count * BADGE_WEIGHT) + (certificates_count * CERTIFICATE_WEIGHT)


@dataclass(frozen=True)
class RankingEntry:
    """Uma linha crua de dados do ranking, antes de virar schema de resposta."""

    user_id: UUID
    name: str
    total_xp: int
    badges_count: int
    certificates_count: int

    @property
    def score(self) -> int:
        return calculate_score(
            total_xp=self.total_xp,
            badges_count=self.badges_count,
            certificates_count=self.certificates_count,
        )


class RankingRepository:
    """Agrega dados de múltiplos domínios (XP, badges, certificados) por usuário.

    Assim como `app.domains.dashboard.repository.DashboardRepository`, esta
    classe só lê tabelas de outros domínios, nunca escreve nelas — a leitura
    combinada não é responsabilidade de nenhum domínio individual.

    Os imports de `UserBadge` (`app.domains.gamification.badges`) e
    `UserCertificate` (`app.domains.gamification.certificates`) são feitos
    dentro dos métodos, não no topo do módulo: no momento em que este arquivo
    foi escrito, os dois módulos estavam sendo criados em paralelo por outras
    tarefas (GAME-002 e GAME-006) e podiam não existir ainda no disco. Isso
    evita que este módulo quebre a importação de todo o domínio
    `gamification` (e, por consequência, o registro de rotas em
    `app/api/v1/router.py`) enquanto a integração final não estiver completa.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _badges_count_subquery(self) -> Subquery:
        from app.domains.gamification.badges import UserBadge

        return (
            select(UserBadge.user_id, func.count().label("badges_count"))
            .where(UserBadge.deleted_at.is_(None))
            .group_by(UserBadge.user_id)
            .subquery()
        )

    def _certificates_count_subquery(self) -> Subquery:
        from app.domains.gamification.certificates import UserCertificate

        return (
            select(UserCertificate.user_id, func.count().label("certificates_count"))
            .where(UserCertificate.deleted_at.is_(None))
            .group_by(UserCertificate.user_id)
            .subquery()
        )

    async def get_all_entries(self) -> list[RankingEntry]:
        """Retorna uma `RankingEntry` por usuário ativo (não deletado) da plataforma.

        Uma única consulta agregada (XP via `LEFT JOIN` + `GROUP BY`, badges e
        certificados via subqueries de contagem, também com `LEFT JOIN` para
        que um usuário sem nenhum badge/certificado apareça com contagem 0
        em vez de ser excluído do resultado).
        """

        xp_subquery = (
            select(
                XpLedger.user_id.label("user_id"),
                func.coalesce(func.sum(XpLedger.amount), 0).label("total_xp"),
            )
            .group_by(XpLedger.user_id)
            .subquery()
        )
        badges_subquery = self._badges_count_subquery()
        certificates_subquery = self._certificates_count_subquery()

        statement = (
            select(
                User.id,
                User.name,
                func.coalesce(xp_subquery.c.total_xp, 0).label("total_xp"),
                func.coalesce(badges_subquery.c.badges_count, 0).label("badges_count"),
                func.coalesce(certificates_subquery.c.certificates_count, 0).label(
                    "certificates_count"
                ),
            )
            .select_from(User)
            .outerjoin(xp_subquery, xp_subquery.c.user_id == User.id)
            .outerjoin(badges_subquery, badges_subquery.c.user_id == User.id)
            .outerjoin(certificates_subquery, certificates_subquery.c.user_id == User.id)
            .where(User.deleted_at.is_(None))
        )
        result = await self._session.execute(statement)

        return [
            RankingEntry(
                user_id=row.id,
                name=row.name,
                total_xp=int(row.total_xp),
                badges_count=int(row.badges_count),
                certificates_count=int(row.certificates_count),
            )
            for row in result.all()
        ]


# --- Schemas -------------------------------------------------------------


class RankingUserEntry(BaseModel):
    """Uma linha do ranking pronta para resposta de API."""

    user_id: UUID
    name: str
    score: int
    position: int


class RankingResponse(BaseModel):
    """Top 10 global + a posição do usuário autenticado (mesmo fora do Top 10).

    `current_user` é `None` apenas no caso defensivo em que o usuário
    autenticado não aparece entre as entradas agregadas (ex.: deletado entre
    a autenticação e a consulta) — não esperado em uso normal, já que
    `get_current_user` já garante um usuário ativo.
    """

    top: list[RankingUserEntry]
    current_user: RankingUserEntry | None
    total_users: int


# --- Service ---------------------------------------------------------------

_TOP_LIMIT = 10


def _rank_entries(entries: list[RankingEntry]) -> list[RankingUserEntry]:
    """Ordena por score desc, com desempate estável por `user_id` (ordem crescente).

    O desempate por `user_id` (não pela ordem de chegada do banco) garante um
    resultado determinístico e reprodutível entre execuções — mesmo critério
    já usado em `app.domains.dashboard.repository.get_ranking_position`
    (`RANK() OVER (ORDER BY total_xp DESC, user_id ASC)`), aqui replicado em
    memória porque o score combina fontes de domínios diferentes que só se
    juntam depois de sair do banco.
    """

    ordered = sorted(entries, key=lambda entry: (-entry.score, entry.user_id))
    return [
        RankingUserEntry(
            user_id=entry.user_id,
            name=entry.name,
            score=entry.score,
            position=position,
        )
        for position, entry in enumerate(ordered, start=1)
    ]


class RankingService:
    def __init__(self, ranking: RankingRepository) -> None:
        self._ranking = ranking

    async def get_global_ranking(self, current_user_id: UUID) -> RankingResponse:
        entries = await self._ranking.get_all_entries()
        ranked = _rank_entries(entries)

        top = ranked[:_TOP_LIMIT]
        current_user = next(
            (entry for entry in ranked if entry.user_id == current_user_id), None
        )

        return RankingResponse(top=top, current_user=current_user, total_users=len(ranked))


# --- Router ------------------------------------------------------------

router = APIRouter(prefix="/gamification", tags=["gamification"])


def get_ranking_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RankingService:
    return RankingService(RankingRepository(session))


@router.get("/ranking")
async def get_ranking(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    ranking_service: Annotated[RankingService, Depends(get_ranking_service)],
) -> SuccessResponse[RankingResponse]:
    ranking = await ranking_service.get_global_ranking(current_user.id)
    return success_response(request, "Ranking recuperado com sucesso.", ranking)
