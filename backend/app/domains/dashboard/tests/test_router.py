from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.model import XpLedger
from app.domains.learning.model import Lesson, Level, Module, Track
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole


async def _create_user(session: AsyncSession, *, email: str, password: str) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
        role=UserRole.STUDENT,
    )
    session.add(user)
    await session.flush()
    return user


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token: str = response.json()["data"]["access_token"]
    return token


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


async def _create_track_with_hierarchy(session: AsyncSession, *, title: str, order: int) -> Track:
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


class TestGetMyDashboard:
    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get("/api/v1/dashboard/me")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_returns_zeroed_state_for_a_brand_new_user_without_content(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, email="dash-me1@claudequest.dev", password="senha-forte")
        token = await _login(
            client_with_db, email="dash-me1@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["xp"] == {"total": 0, "level": 1, "xp_to_next_level": 250}
        assert data["streak"] == {"current_days": 0, "last_active_date": None}
        assert data["ranking"]["position"] is not None
        assert data["ranking"]["total_users"] >= 1
        assert data["next_lesson"] is None
        assert data["badges"] == []
        assert data["certificates"] == []

    async def test_returns_next_lesson_when_content_exists(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_track_with_hierarchy(db_session, title="Trilha B", order=2)
        track_a = await _create_track_with_hierarchy(db_session, title="Trilha A", order=1)
        await _create_user(db_session, email="dash-me2@claudequest.dev", password="senha-forte")
        token = await _login(
            client_with_db, email="dash-me2@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        next_lesson = response.json()["data"]["next_lesson"]
        assert next_lesson is not None
        assert next_lesson["track_title"] == track_a.title
        assert next_lesson["lesson_title"] == f"Missão de {track_a.title}"

    async def test_reflects_xp_and_multi_day_streak(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_user(
            db_session, email="dash-me3@claudequest.dev", password="senha-forte"
        )
        token = await _login(
            client_with_db, email="dash-me3@claudequest.dev", password="senha-forte"
        )
        today = datetime.now(UTC)
        await _add_xp(db_session, user_id=user.id, amount=300, reason="quiz", created_at=today)
        await _add_xp(
            db_session,
            user_id=user.id,
            amount=100,
            reason="quiz",
            created_at=today - timedelta(days=1),
        )
        await _add_xp(
            db_session,
            user_id=user.id,
            amount=100,
            reason="quiz",
            created_at=today - timedelta(days=2),
        )

        response = await client_with_db.get(
            "/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["xp"]["total"] == 500
        assert data["streak"]["current_days"] == 3
        assert data["streak"]["last_active_date"] == today.date().isoformat()

    async def test_ranking_reflects_multiple_users(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        top_user = await _create_user(
            db_session, email="dash-me4-top@claudequest.dev", password="senha-forte"
        )
        await _create_user(
            db_session, email="dash-me4-bottom@claudequest.dev", password="senha-forte"
        )
        await _add_xp(db_session, user_id=top_user.id, amount=5000, reason="quiz")
        token = await _login(
            client_with_db, email="dash-me4-top@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        ranking = response.json()["data"]["ranking"]
        assert ranking["position"] == 1
        assert ranking["total_users"] >= 2
