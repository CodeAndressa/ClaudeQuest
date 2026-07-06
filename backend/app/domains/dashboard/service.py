from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.domains.dashboard.repository import DashboardRepository
from app.domains.dashboard.schemas import (
    DashboardNextLesson,
    DashboardRanking,
    DashboardResponse,
    DashboardStreak,
    DashboardXp,
)
from app.domains.gamification.xp_rules import calculate_level, xp_to_next_level


class DashboardService:
    def __init__(self, dashboard: DashboardRepository) -> None:
        self._dashboard = dashboard

    async def get_summary(self, user_id: UUID) -> DashboardResponse:
        total_xp = await self._dashboard.get_total_xp(user_id)
        xp = DashboardXp(
            total=total_xp,
            level=calculate_level(total_xp),
            xp_to_next_level=xp_to_next_level(total_xp),
        )

        active_dates = await self._dashboard.get_distinct_xp_dates_desc(user_id)
        streak = self._calculate_streak(active_dates)

        position = await self._dashboard.get_ranking_position(user_id)
        total_users = await self._dashboard.get_total_users()
        ranking = DashboardRanking(position=position, total_users=total_users)

        next_lesson = await self._build_next_lesson()

        return DashboardResponse(
            xp=xp,
            streak=streak,
            ranking=ranking,
            next_lesson=next_lesson,
            badges=[],
            certificates=[],
        )

    @staticmethod
    def _calculate_streak(active_dates_desc: list[date]) -> DashboardStreak:
        """Conta dias consecutivos com pelo menos um XpLedger, a partir de hoje (UTC).

        `active_dates_desc` já vem ordenada da mais recente para a mais antiga
        (uma linha por dia distinto, sem duplicatas — garantido pelo `GROUP BY`
        do Repository). A contagem para no primeiro "buraco": se o usuário não
        tem XP hoje, o streak é 0 mesmo que tenha estudado ontem — regra do
        Gamification Engine ("Streak... incrementa apenas quando o usuário
        conclui pelo menos uma missão", contado dia a dia sem tolerância).
        """

        if not active_dates_desc:
            return DashboardStreak(current_days=0, last_active_date=None)

        today = datetime.now(UTC).date()
        last_active_date = active_dates_desc[0]

        if last_active_date != today:
            return DashboardStreak(current_days=0, last_active_date=last_active_date)

        current_days = 0
        expected_date = today
        for active_date in active_dates_desc:
            if active_date != expected_date:
                break
            current_days += 1
            expected_date = expected_date - timedelta(days=1)

        return DashboardStreak(current_days=current_days, last_active_date=last_active_date)

    async def _build_next_lesson(self) -> DashboardNextLesson | None:
        result = await self._dashboard.get_first_lesson_of_first_active_track()
        if result is None:
            return None
        track_title, lesson = result
        return DashboardNextLesson(
            track_title=track_title,
            lesson_title=lesson.title,
            lesson_id=lesson.id,
        )
