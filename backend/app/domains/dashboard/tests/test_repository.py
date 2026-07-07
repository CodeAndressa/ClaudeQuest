from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.dashboard.repository import DashboardRepository
from app.domains.gamification.model import XpLedger
from app.domains.learning.model import Lesson, Level, Module, School, Track, UserLessonProgress
from app.domains.organizations.model import Organization
from app.domains.users.model import User


async def _create_user(session: AsyncSession, *, email: str) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="UsuÃ¡ria de Teste",
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


async def _create_school(session: AsyncSession, *, title: str) -> School:
    school = School(
        title=title,
        slug=title.lower().replace(" ", "-"),
        description="Escola de IA aplicada.",
        order=1,
        is_active=True,
    )
    session.add(school)
    await session.flush()
    return school


async def _create_track_with_hierarchy(session: AsyncSession, *, order: int, title: str) -> Track:
    school = await _create_school(session, title=f"Escola {title}")
    track = Track(
        school_id=school.id,
        title=title,
        description="DescriÃ§Ã£o",
        difficulty="beginner",
        estimated_hours=1,
        order=order,
    )
    session.add(track)
    await session.flush()

    module = Module(track_id=track.id, title="MÃ³dulo", description="DescriÃ§Ã£o", order=1)
    session.add(module)
    await session.flush()

    level = Level(module_id=module.id, title="NÃ­vel 1", description="DescriÃ§Ã£o", level_number=1)
    session.add(level)
    await session.flush()

    lesson = Lesson(
        level_id=level.id,
        title=f"MissÃ£o de {title}",
        description="DescriÃ§Ã£o",
        content="ConteÃºdo",
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


class TestGetNextIncompleteLesson:
    async def test_returns_none_when_no_active_track_exists(
        self, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, email="dash-next-none@claudequest.dev")
        repository = DashboardRepository(db_session)

        result = await repository.get_next_incomplete_lesson(user.id)

        assert result is None

    async def test_returns_first_lesson_of_first_track_by_order(
        self, db_session: AsyncSession
    ) -> None:
        user = await _create_user(db_session, email="dash-next-order@claudequest.dev")
        repository = DashboardRepository(db_session)
        await _create_track_with_hierarchy(db_session, order=2, title="Trilha B")
        track_a = await _create_track_with_hierarchy(db_session, order=1, title="Trilha A")

        result = await repository.get_next_incomplete_lesson(user.id)

        assert result is not None
        track, lesson = result
        assert track.id == track_a.id
        assert track.title == track_a.title
        assert lesson.title == "MissÃ£o de Trilha A"

    async def test_ignores_inactive_tracks(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, email="dash-next-active@claudequest.dev")
        repository = DashboardRepository(db_session)
        inactive_track = await _create_track_with_hierarchy(
            db_session, order=1, title="Trilha Inativa"
        )
        inactive_track.is_active = False
        await db_session.flush()
        active_track = await _create_track_with_hierarchy(
            db_session, order=2, title="Trilha Ativa"
        )

        result = await repository.get_next_incomplete_lesson(user.id)

        assert result is not None
        track, _lesson = result
        assert track.title == active_track.title

    async def test_skips_completed_lessons(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, email="dash-next-completed@claudequest.dev")
        track = await _create_track_with_hierarchy(db_session, order=1, title="Trilha Progresso")
        level_id = await db_session.scalar(
            select(Level.id)
            .join(Module, Module.id == Level.module_id)
            .where(Module.track_id == track.id)
        )
        assert level_id is not None
        first_lesson = await db_session.scalar(
            select(Lesson).where(Lesson.level_id == level_id, Lesson.order == 1)
        )
        assert first_lesson is not None
        second_lesson = Lesson(
            level_id=level_id,
            title="Segunda missao",
            description="Descricao",
            content="Conteudo",
            order=2,
        )
        db_session.add(second_lesson)
        await db_session.flush()
        db_session.add(
            UserLessonProgress(
                user_id=user.id,
                lesson_id=first_lesson.id,
                completed_at=datetime.now(UTC),
                xp_awarded=first_lesson.xp,
            )
        )
        await db_session.flush()
        repository = DashboardRepository(db_session)

        result = await repository.get_next_incomplete_lesson(user.id)

        assert result is not None
        _track, lesson = result
        assert lesson.id == second_lesson.id
