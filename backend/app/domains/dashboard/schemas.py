import uuid
from datetime import date

from pydantic import BaseModel


class DashboardXp(BaseModel):
    """XP e nível atuais do usuário (mesma regra de `app.domains.gamification`)."""

    total: int
    level: int
    xp_to_next_level: int


class DashboardStreak(BaseModel):
    """Dias consecutivos de estudo, contados a partir de hoje (UTC)."""

    current_days: int
    last_active_date: date | None


class DashboardRanking(BaseModel):
    """Posição do usuário no ranking global de XP."""

    position: int | None
    total_users: int


class DashboardNextLesson(BaseModel):
    """Próxima missão sugerida ao usuário."""

    track_title: str
    lesson_title: str
    lesson_id: uuid.UUID


class DashboardResponse(BaseModel):
    """Resumo agregado do Módulo Dashboard (GET /api/v1/dashboard/me).

    `badges` e `certificates` são sempre listas vazias nesta primeira fatia —
    as tabelas correspondentes ainda não existem (ficam para os épicos futuros
    GAME-002/003 e CERT-001, conforme a Functional Specification).
    """

    xp: DashboardXp
    streak: DashboardStreak
    ranking: DashboardRanking
    next_lesson: DashboardNextLesson | None
    badges: list[str]
    certificates: list[str]
