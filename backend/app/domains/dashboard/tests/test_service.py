from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domains.dashboard.service import DashboardService
from app.domains.gamification.xp_rules import xp_required_for_level
from app.domains.learning.model import Lesson


class _FakeDashboardRepository:
    def __init__(self) -> None:
        self.total_xp = 0
        self.active_dates: list[date] = []
        self.ranking_position: int | None = 1
        self.total_users = 1
        self.next_lesson_result: tuple[str, Lesson] | None = None

    async def get_total_xp(self, user_id: UUID) -> int:
        return self.total_xp

    async def get_distinct_xp_dates_desc(self, user_id: UUID) -> list[date]:
        return self.active_dates

    async def get_ranking_position(self, user_id: UUID) -> int | None:
        return self.ranking_position

    async def get_total_users(self) -> int:
        return self.total_users

    async def get_first_lesson_of_first_active_track(self) -> tuple[str, Lesson] | None:
        return self.next_lesson_result


@pytest.fixture
def fake_repository() -> _FakeDashboardRepository:
    return _FakeDashboardRepository()


@pytest.fixture
def service(fake_repository: _FakeDashboardRepository) -> DashboardService:
    return DashboardService(fake_repository)  # type: ignore[arg-type]


class TestGetSummaryXp:
    async def test_new_user_has_zero_xp_and_level_1(self, service: DashboardService) -> None:
        summary = await service.get_summary(uuid4())

        assert summary.xp.total == 0
        assert summary.xp.level == 1
        assert summary.xp.xp_to_next_level == xp_required_for_level(2)

    async def test_reflects_accumulated_xp(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        fake_repository.total_xp = 600

        summary = await service.get_summary(uuid4())

        assert summary.xp.total == 600
        assert summary.xp.level >= 2


class TestGetSummaryStreak:
    async def test_no_entries_means_zero_streak_and_no_last_active_date(
        self, service: DashboardService
    ) -> None:
        summary = await service.get_summary(uuid4())

        assert summary.streak.current_days == 0
        assert summary.streak.last_active_date is None

    async def test_streak_is_zero_when_last_active_date_is_not_today(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
        fake_repository.active_dates = [yesterday]

        summary = await service.get_summary(uuid4())

        assert summary.streak.current_days == 0
        assert summary.streak.last_active_date == yesterday

    async def test_counts_consecutive_days_ending_today(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        today = datetime.now(UTC).date()
        fake_repository.active_dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
        ]

        summary = await service.get_summary(uuid4())

        assert summary.streak.current_days == 3
        assert summary.streak.last_active_date == today

    async def test_stops_counting_at_first_gap(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        today = datetime.now(UTC).date()
        fake_repository.active_dates = [
            today,
            today - timedelta(days=1),
            # buraco: falta today - 2 dias
            today - timedelta(days=3),
        ]

        summary = await service.get_summary(uuid4())

        assert summary.streak.current_days == 2
        assert summary.streak.last_active_date == today


class TestGetSummaryRanking:
    async def test_reflects_position_and_total_users(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        fake_repository.ranking_position = 3
        fake_repository.total_users = 42

        summary = await service.get_summary(uuid4())

        assert summary.ranking.position == 3
        assert summary.ranking.total_users == 42

    async def test_position_can_be_none(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        fake_repository.ranking_position = None

        summary = await service.get_summary(uuid4())

        assert summary.ranking.position is None


class TestGetSummaryNextLesson:
    async def test_is_none_when_no_content_exists(self, service: DashboardService) -> None:
        summary = await service.get_summary(uuid4())

        assert summary.next_lesson is None

    async def test_reflects_repository_result(
        self, service: DashboardService, fake_repository: _FakeDashboardRepository
    ) -> None:
        lesson = Lesson(
            id=uuid4(),
            level_id=uuid4(),
            title="Primeira missão",
            description="Descrição",
            content="Conteúdo",
            order=1,
        )
        fake_repository.next_lesson_result = ("Claude Chat", lesson)

        summary = await service.get_summary(uuid4())

        assert summary.next_lesson is not None
        assert summary.next_lesson.track_title == "Claude Chat"
        assert summary.next_lesson.lesson_title == "Primeira missão"
        assert summary.next_lesson.lesson_id == lesson.id


class TestGetSummaryBadgesAndCertificates:
    async def test_are_always_empty_lists(self, service: DashboardService) -> None:
        summary = await service.get_summary(uuid4())

        assert summary.badges == []
        assert summary.certificates == []
