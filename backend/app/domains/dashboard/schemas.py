import uuid
from datetime import date

from pydantic import BaseModel


class DashboardXp(BaseModel):
    """XP e nÃ­vel atuais do usuÃ¡rio (mesma regra de `app.domains.gamification`)."""

    total: int
    level: int
    xp_to_next_level: int


class DashboardStreak(BaseModel):
    """Dias consecutivos de estudo, contados a partir de hoje (UTC)."""

    current_days: int
    last_active_date: date | None


class DashboardRanking(BaseModel):
    """PosiÃ§Ã£o do usuÃ¡rio no ranking global de XP."""

    position: int | None
    total_users: int


class DashboardNextLesson(BaseModel):
    """PrÃ³xima missÃ£o sugerida ao usuÃ¡rio."""

    track_id: uuid.UUID
    track_title: str
    lesson_title: str
    lesson_id: uuid.UUID


class DashboardResponse(BaseModel):
    """Resumo agregado do MÃ³dulo Dashboard (GET /api/v1/dashboard/me).

    `badges` e `certificates` sÃ£o sempre listas vazias nesta primeira fatia â€”
    as tabelas correspondentes ainda nÃ£o existem (ficam para os Ã©picos futuros
    GAME-002/003 e CERT-001, conforme a Functional Specification).
    """

    xp: DashboardXp
    streak: DashboardStreak
    ranking: DashboardRanking
    next_lesson: DashboardNextLesson | None
    badges: list[str]
    certificates: list[str]
