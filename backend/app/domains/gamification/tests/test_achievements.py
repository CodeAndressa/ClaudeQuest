import uuid
from datetime import UTC, date, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.achievements import (
    Achievement,
    AchievementMetric,
    AchievementRepository,
    AchievementService,
    UserAchievementRepository,
    UserMetricsRepository,
    _calculate_streak_days,
)
from app.domains.gamification.badges import Badge, BadgeCategory, UserBadge
from app.domains.gamification.certificates import Certificate, UserCertificate
from app.domains.gamification.model import XpLedger
from app.domains.learning.model import (
    Lesson,
    Level,
    Module,
    School,
    Track,
    UserLessonProgress,
)
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole


async def _create_user(
    session: AsyncSession, *, email: str, password: str, role: UserRole = UserRole.STUDENT
) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_achievement(
    session: AsyncSession,
    *,
    name: str = "Primeira Missão",
    metric: AchievementMetric = AchievementMetric.LESSONS_COMPLETED,
    threshold: int = 1,
) -> Achievement:
    achievement = Achievement(
        name=name,
        description=f"Descrição de {name}",
        icon="footprints",
        metric=metric,
        threshold=threshold,
    )
    session.add(achievement)
    await session.flush()
    return achievement


async def _create_lesson_chain(session: AsyncSession) -> tuple[Lesson, Track]:
    school = School(
        title="Escola de Teste",
        slug=f"escola-{uuid.uuid4()}",
        description="Descrição",
        order=1,
        is_active=True,
    )
    session.add(school)
    await session.flush()

    track = Track(
        school_id=school.id,
        title="Trilha de Teste",
        description="Descrição",
        difficulty="beginner",
        estimated_hours=1,
        order=1,
    )
    session.add(track)
    await session.flush()

    module = Module(track_id=track.id, title="Módulo de Teste", description="Descrição", order=1)
    session.add(module)
    await session.flush()

    level = Level(
        module_id=module.id, title="Nível de Teste", description="Descrição", level_number=1
    )
    session.add(level)
    await session.flush()

    lesson = Lesson(
        level_id=level.id,
        title="Lição de Teste",
        description="Descrição",
        content="Conteúdo",
        order=1,
    )
    session.add(lesson)
    await session.flush()
    return lesson, track


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token: str = response.json()["data"]["access_token"]
    return token


# --------------------------------------------------------------------------- #
# _calculate_streak_days
# --------------------------------------------------------------------------- #


class TestCalculateStreakDays:
    def test_returns_zero_when_no_activity(self) -> None:
        assert _calculate_streak_days([], today=date(2026, 7, 8)) == 0

    def test_returns_zero_when_most_recent_activity_is_not_today(self) -> None:
        assert _calculate_streak_days([date(2026, 7, 7)], today=date(2026, 7, 8)) == 0

    def test_counts_consecutive_days_ending_today(self) -> None:
        dates = [date(2026, 7, 8), date(2026, 7, 7), date(2026, 7, 6)]
        assert _calculate_streak_days(dates, today=date(2026, 7, 8)) == 3

    def test_stops_at_first_gap(self) -> None:
        dates = [date(2026, 7, 8), date(2026, 7, 7), date(2026, 7, 4)]
        assert _calculate_streak_days(dates, today=date(2026, 7, 8)) == 2


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class TestAchievementRepository:
    async def test_create_and_get_by_id(self, db_session: AsyncSession) -> None:
        repository = AchievementRepository(db_session)

        achievement = await repository.create(
            name="Lenda",
            description="5000 XP",
            icon="crown",
            metric=AchievementMetric.TOTAL_XP,
            threshold=5000,
        )

        found = await repository.get_by_id(achievement.id)
        assert found is not None
        assert found.name == "Lenda"

    async def test_get_by_id_returns_none_for_unknown_id(self, db_session: AsyncSession) -> None:
        repository = AchievementRepository(db_session)

        assert await repository.get_by_id(uuid.uuid4()) is None

    async def test_list_all_returns_created_achievements(self, db_session: AsyncSession) -> None:
        await _create_achievement(db_session, name="Primeira Missão")
        await _create_achievement(db_session, name="Maratonista", threshold=50)
        repository = AchievementRepository(db_session)

        achievements = await repository.list_all()

        names = {achievement.name for achievement in achievements}
        assert {"Primeira Missão", "Maratonista"} <= names


class TestUserMetricsRepository:
    async def test_get_total_xp_sums_ledger_entries(self, db_session: AsyncSession) -> None:
        user = await _create_user(
            db_session, email="metrics-xp@claudequest.dev", password="senha-forte"
        )
        db_session.add(XpLedger(user_id=user.id, amount=30, reason="teste"))
        db_session.add(XpLedger(user_id=user.id, amount=20, reason="teste"))
        await db_session.flush()
        repository = UserMetricsRepository(db_session)

        total = await repository.get_total_xp(user.id)

        assert total == 50

    async def test_get_lessons_completed_count(self, db_session: AsyncSession) -> None:
        user = await _create_user(
            db_session, email="metrics-lessons@claudequest.dev", password="senha-forte"
        )
        lesson, _track = await _create_lesson_chain(db_session)
        db_session.add(
            UserLessonProgress(
                user_id=user.id,
                lesson_id=lesson.id,
                completed_at=datetime.now(UTC),
                xp_awarded=10,
            )
        )
        await db_session.flush()
        repository = UserMetricsRepository(db_session)

        count = await repository.get_lessons_completed_count(user.id)

        assert count == 1

    async def test_get_badges_count(self, db_session: AsyncSession) -> None:
        user = await _create_user(
            db_session, email="metrics-badges@claudequest.dev", password="senha-forte"
        )
        badge = Badge(name="Badge de Teste", description="Desc", category=BadgeCategory.BRONZE)
        db_session.add(badge)
        await db_session.flush()
        db_session.add(UserBadge(user_id=user.id, badge_id=badge.id, earned_at=datetime.now(UTC)))
        await db_session.flush()
        repository = UserMetricsRepository(db_session)

        count = await repository.get_badges_count(user.id)

        assert count == 1

    async def test_get_certificates_count(self, db_session: AsyncSession) -> None:
        user = await _create_user(
            db_session, email="metrics-certs@claudequest.dev", password="senha-forte"
        )
        _lesson, track = await _create_lesson_chain(db_session)
        certificate = Certificate(track_id=track.id, title="Cert", hours=1)
        db_session.add(certificate)
        await db_session.flush()
        db_session.add(
            UserCertificate(
                certificate_id=certificate.id,
                user_id=user.id,
                validation_code="codigo-teste",
                issued_at=datetime.now(UTC),
                pdf_url=None,
            )
        )
        await db_session.flush()
        repository = UserMetricsRepository(db_session)

        count = await repository.get_certificates_count(user.id)

        assert count == 1


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class TestEvaluateAndGrant:
    async def test_grants_achievement_when_threshold_is_met(
        self, db_session: AsyncSession
    ) -> None:
        user = await _create_user(
            db_session, email="eval-grant1@claudequest.dev", password="senha-forte"
        )
        await _create_achievement(
            db_session,
            name="Lenda",
            metric=AchievementMetric.TOTAL_XP,
            threshold=100,
        )
        db_session.add(XpLedger(user_id=user.id, amount=150, reason="teste"))
        await db_session.flush()

        service = AchievementService(
            AchievementRepository(db_session),
            UserAchievementRepository(db_session),
            UserMetricsRepository(db_session),
        )

        await service.evaluate_and_grant(user.id)

        granted = await service.list_for_user(user.id)
        assert len(granted) == 1
        assert granted[0].achievement.name == "Lenda"

    async def test_does_not_grant_when_threshold_is_not_met(
        self, db_session: AsyncSession
    ) -> None:
        user = await _create_user(
            db_session, email="eval-grant2@claudequest.dev", password="senha-forte"
        )
        await _create_achievement(
            db_session,
            name="Lenda",
            metric=AchievementMetric.TOTAL_XP,
            threshold=5000,
        )
        db_session.add(XpLedger(user_id=user.id, amount=10, reason="teste"))
        await db_session.flush()

        service = AchievementService(
            AchievementRepository(db_session),
            UserAchievementRepository(db_session),
            UserMetricsRepository(db_session),
        )

        await service.evaluate_and_grant(user.id)

        granted = await service.list_for_user(user.id)
        assert granted == []

    async def test_is_idempotent_when_called_twice(self, db_session: AsyncSession) -> None:
        user = await _create_user(
            db_session, email="eval-grant3@claudequest.dev", password="senha-forte"
        )
        await _create_achievement(
            db_session,
            name="Lenda",
            metric=AchievementMetric.TOTAL_XP,
            threshold=100,
        )
        db_session.add(XpLedger(user_id=user.id, amount=150, reason="teste"))
        await db_session.flush()

        service = AchievementService(
            AchievementRepository(db_session),
            UserAchievementRepository(db_session),
            UserMetricsRepository(db_session),
        )

        await service.evaluate_and_grant(user.id)
        await service.evaluate_and_grant(user.id)

        granted = await service.list_for_user(user.id)
        assert len(granted) == 1


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #


class TestListAchievementCatalog:
    async def test_returns_full_catalog_for_any_authenticated_user(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_achievement(db_session, name="Primeira Missão")
        await _create_achievement(db_session, name="Maratonista", threshold=50)
        await _create_user(
            db_session, email="achv-cat1@claudequest.dev", password="senha-forte"
        )
        token = await _login(
            client_with_db, email="achv-cat1@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/gamification/achievements", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        names = {item["name"] for item in response.json()["data"]}
        assert {"Primeira Missão", "Maratonista"} <= names

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get("/api/v1/gamification/achievements")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


class TestListMyAchievements:
    async def test_evaluates_and_grants_lazily_on_read(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_achievement(
            db_session,
            name="Primeira Missão",
            metric=AchievementMetric.LESSONS_COMPLETED,
            threshold=1,
        )
        student = await _create_user(
            db_session, email="achv-me1@claudequest.dev", password="senha-forte"
        )
        lesson, _track = await _create_lesson_chain(db_session)
        db_session.add(
            UserLessonProgress(
                user_id=student.id,
                lesson_id=lesson.id,
                completed_at=datetime.now(UTC),
                xp_awarded=10,
            )
        )
        await db_session.flush()
        await db_session.commit()
        token = await _login(
            client_with_db, email="achv-me1@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/gamification/me/achievements",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["achievement"]["name"] == "Primeira Missão"

    async def test_returns_empty_list_when_no_thresholds_are_met(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_achievement(
            db_session,
            name="Lenda",
            metric=AchievementMetric.TOTAL_XP,
            threshold=5000,
        )
        await _create_user(
            db_session, email="achv-me2@claudequest.dev", password="senha-forte"
        )
        token = await _login(
            client_with_db, email="achv-me2@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/gamification/me/achievements",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestCreateAchievement:
    async def test_admin_can_create_a_new_rule(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="achv-create-admin1@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.post(
            "/api/v1/gamification/achievements",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Colecionador",
                "description": "10 badges",
                "icon": "gem",
                "metric": "badges_count",
                "threshold": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Colecionador"
        assert data["metric"] == "badges_count"
        assert data["threshold"] == 10

    async def test_non_admin_is_forbidden_from_creating(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="achv-create-student1@claudequest.dev", password="senha-forte"
        )
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.post(
            "/api/v1/gamification/achievements",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Colecionador",
                "description": "10 badges",
                "icon": "gem",
                "metric": "badges_count",
                "threshold": 10,
            },
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.post(
            "/api/v1/gamification/achievements",
            json={
                "name": "Colecionador",
                "description": "10 badges",
                "icon": "gem",
                "metric": "badges_count",
                "threshold": 10,
            },
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
