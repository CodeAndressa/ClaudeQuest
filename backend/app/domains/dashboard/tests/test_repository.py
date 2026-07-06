from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.dashboard.repository import DashboardRepository
from app.domains.gamification.model import XpLedger
from app.domains.learning.model import Lesson, Level, Module, Track
from app.domains.organizations.model import Organization
from app.domains.users.model import User


async def _create_user(session: AsyncSession, *, email: str) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password("senha-forte"),
    )
    session.add(user)
    await session.flush()
    return user


async def _add_xp(
    session: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    reason: str,
    created_at: datetime | None = None,
) -> XpLedger:
    entry = XpLedger(user_id=user_id, amount=amount, reason=reason)
    session.add(entry)
    await session.flush()
    if created_at is not None:
        await session.execute(
            update(XpLedger).where(XpLedger.id == entry.id).values(created_at=created_at)
        )
        await session.flush()
    return entry


async def _create_track_with_hierarchy(session: AsyncSession, *, order: int, title: str) -> Track:
    track = Track(
        title=title,
        description="Descrição",
        difficulty="beginner",
        estimated_hours=1,
        order=order,
    )
    session.add(track)
    await session.flush()

    module = Module(track_id=track.id, title="Módulo", description="Descrição", order=1)
    session.add(module)
    await session.flush()

    level = Level(module_id=module.id, title="Nível 1", description="Descrição", level_number=1)
    session.add(level)
    await session.flush()

    lesson = Lesson(
        level_id=level.id,
        title=f"Missão de {title}",
        description="Descrição",
        content="Conteúdo",
        order=1,
    )
    session.add(lesson)
    await session.flush()

    return track


class TestGetTotalXp:
    async def test_returns_zero_when_no_entries(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, email="dash-repo1@claudequest.dev")
        repository = DashboardRepository(db_session)

        total = await repository.get_total_xp(user.id)

        assert total == 0

    async def test_sums_all_entries(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, email="dash-repo2@claudequest.dev")
        repository = DashboardRepository(db_session)
        await _add_xp(db_session, user_id=user.id, amount=100, reason="quiz")
        await _add_xp(db_session, user_id=user.id, amount=50, reason="streak")

        total = await repository.get_total_xp(user.id)

        assert total == 150


class TestGetDistinctXpDatesDesc:
    async def test_returns_empty_list_when_no_entries(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, email="dash-repo3@claudequest.dev")
        repository = DashboardRepository(db_session)

        dates = await repository.get_distinct_xp_dates_desc(user.id)

        assert dates == []

    async def test_deduplicates_same_day_entries_and_orders_desc(
        self, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, email="dash-repo4@claudequest.dev")
        repository = DashboardRepository(db_session)
        today = datetime.now(UTC)
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        await _add_xp(db_session, user_id=user.id, amount=10, reason="a", created_at=today)
        await _add_xp(db_session, user_id=user.id, amount=10, reason="b", created_at=today)
        await _add_xp(db_session, user_id=user.id, amount=10, reason="c", created_at=yesterday)
        await _add_xp(
            db_session, user_id=user.id, amount=10, reason="d", created_at=two_days_ago
        )

        dates = await repository.get_distinct_xp_dates_desc(user.id)

        assert dates == [today.date(), yesterday.date(), two_days_ago.date()]


class TestRanking:
    async def test_get_total_users_counts_all_users(self, db_session: AsyncSession) -> None:
        await _create_user(db_session, email="dash-repo5a@claudequest.dev")
        await _create_user(db_session, email="dash-repo5b@claudequest.dev")
        repository = DashboardRepository(db_session)

        total = await repository.get_total_users()

        assert total >= 2

    async def test_get_ranking_position_orders_by_total_xp_desc(
        self, db_session: AsyncSession
    ) -> None:
        repository = DashboardRepository(db_session)
        top_user = await _create_user(db_session, email="dash-rank-top@claudequest.dev")
        mid_user = await _create_user(db_session, email="dash-rank-mid@claudequest.dev")
        low_user = await _create_user(db_session, email="dash-rank-low@claudequest.dev")

        await _add_xp(db_session, user_id=top_user.id, amount=1000, reason="quiz")
        await _add_xp(db_session, user_id=mid_user.id, amount=500, reason="quiz")
        await _add_xp(db_session, user_id=low_user.id, amount=10, reason="quiz")

        top_position = await repository.get_ranking_position(top_user.id)
        mid_position = await repository.get_ranking_position(mid_user.id)
        low_position = await repository.get_ranking_position(low_user.id)

        assert top_position is not None
        assert mid_position is not None
        assert low_position is not None
        assert top_position < mid_position < low_position

    async def test_get_ranking_position_breaks_ties_stably_by_id(
        self, db_session: AsyncSession
    ) -> None:
        repository = DashboardRepository(db_session)
        user_a = await _create_user(db_session, email="dash-rank-tie-a@claudequest.dev")
        user_b = await _create_user(db_session, email="dash-rank-tie-b@claudequest.dev")
        await _add_xp(db_session, user_id=user_a.id, amount=200, reason="quiz")
        await _add_xp(db_session, user_id=user_b.id, amount=200, reason="quiz")

        position_a = await repository.get_ranking_position(user_a.id)
        position_b = await repository.get_ranking_position(user_b.id)
        assert position_a is not None
        assert position_b is not None

        expected_first, _expected_second = sorted([user_a.id, user_b.id])
        if user_a.id == expected_first:
            assert position_a < position_b
        else:
            assert position_b < position_a

    async def test_get_ranking_position_includes_users_without_any_xp(
        self, db_session: AsyncSession
    ) -> None:
        repository = DashboardRepository(db_session)
        user = await _create_user(db_session, email="dash-rank-zero@claudequest.dev")

        position = await repository.get_ranking_position(user.id)

        assert position is not None


class TestGetFirstLessonOfFirstActiveTrack:
    async def test_returns_none_when_no_active_track_exists(
        self, db_session: AsyncSession
    ) -> None:
        repository = DashboardRepository(db_session)

        result = await repository.get_first_lesson_of_first_active_track()

        assert result is None

    async def test_returns_first_lesson_of_first_track_by_order(
        self, db_session: AsyncSession
    ) -> None:
        repository = DashboardRepository(db_session)
        await _create_track_with_hierarchy(db_session, order=2, title="Trilha B")
        track_a = await _create_track_with_hierarchy(db_session, order=1, title="Trilha A")

        result = await repository.get_first_lesson_of_first_active_track()

        assert result is not None
        track_title, lesson = result
        assert track_title == track_a.title
        assert lesson.title == "Missão de Trilha A"

    async def test_ignores_inactive_tracks(self, db_session: AsyncSession) -> None:
        repository = DashboardRepository(db_session)
        inactive_track = await _create_track_with_hierarchy(
            db_session, order=1, title="Trilha Inativa"
        )
        inactive_track.is_active = False
        await db_session.flush()
        active_track = await _create_track_with_hierarchy(
            db_session, order=2, title="Trilha Ativa"
        )

        result = await repository.get_first_lesson_of_first_active_track()

        assert result is not None
        track_title, _lesson = result
        assert track_title == active_track.title
