"""Testes de integração de RankingRepository e do endpoint /gamification/ranking
contra um banco real — os testes em test_ranking.py usam um repositório fake e
nunca exercitam a query SQL de verdade (joins, subqueries, coalesce)."""

from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.badges import Badge, BadgeCategory, UserBadge
from app.domains.gamification.certificates import Certificate, UserCertificate
from app.domains.gamification.model import XpLedger
from app.domains.gamification.ranking import RankingRepository
from app.domains.learning.model import School, Track
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole


async def _create_user(
    session: AsyncSession, *, email: str, name: str = "Usuária de Teste"
) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name=name,
        email=email,
        password_hash=hash_password("senha-forte"),
        role=UserRole.STUDENT,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_school(session: AsyncSession, *, title: str = "Claude Academy") -> School:
    school = School(
        title=title,
        slug=f"{title.lower().replace(' ', '-')}-{uuid4()}",
        description="Escola de IA aplicada.",
        order=1,
        is_active=True,
    )
    session.add(school)
    await session.flush()
    return school


async def test_get_all_entries_returns_zeroed_entry_for_user_without_any_data(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="zerado@claudequest.dev")

    entries = await RankingRepository(db_session).get_all_entries()

    entry = next(e for e in entries if e.user_id == user.id)
    assert entry.total_xp == 0
    assert entry.badges_count == 0
    assert entry.certificates_count == 0
    assert entry.score == 0


async def test_get_all_entries_aggregates_xp_badges_and_certificates(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="completo@claudequest.dev")

    db_session.add(XpLedger(user_id=user.id, amount=100, reason="teste"))
    db_session.add(XpLedger(user_id=user.id, amount=50, reason="teste-2"))

    badge = Badge(name="Badge X", description="x", category=BadgeCategory.OURO)
    db_session.add(badge)
    await db_session.flush()
    db_session.add(UserBadge(user_id=user.id, badge_id=badge.id, earned_at=datetime.now(UTC)))

    school = await _create_school(db_session, title="Escola Ranking")
    track = Track(
        school_id=school.id,
        title="Trilha Teste",
        description="x",
        difficulty="beginner",
        estimated_hours=1,
        order=1,
    )
    db_session.add(track)
    await db_session.flush()

    certificate = Certificate(track_id=track.id, title="Cert Teste", hours=10)
    db_session.add(certificate)
    await db_session.flush()
    db_session.add(
        UserCertificate(
            certificate_id=certificate.id,
            user_id=user.id,
            validation_code="codigo-unico-ranking-teste",
            issued_at=badge.created_at,
        )
    )
    await db_session.flush()

    entries = await RankingRepository(db_session).get_all_entries()

    entry = next(e for e in entries if e.user_id == user.id)
    assert entry.total_xp == 150
    assert entry.badges_count == 1
    assert entry.certificates_count == 1
    assert entry.score == 150 + 100 + 500


async def test_ranking_endpoint_returns_top_and_current_user(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="ranking-me@claudequest.dev", name="Eu Mesma")
    db_session.add(XpLedger(user_id=user.id, amount=10, reason="x"))
    await db_session.flush()

    login_response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "ranking-me@claudequest.dev", "password": "senha-forte"},
    )
    access_token = login_response.json()["data"]["access_token"]

    response = await client_with_db.get(
        "/api/v1/gamification/ranking", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["current_user"] is not None
    assert isinstance(body["top"], list)
    assert len(body["top"]) <= 10


async def test_ranking_endpoint_requires_authentication(client_with_db: httpx.AsyncClient) -> None:
    response = await client_with_db.get("/api/v1/gamification/ranking")

    assert response.status_code == 401
