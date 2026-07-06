import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.badges import (
    Badge,
    BadgeCategory,
    BadgeRepository,
    UserBadgeRepository,
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


async def _create_badge(
    session: AsyncSession,
    *,
    name: str = "Primeiro Login",
    category: BadgeCategory = BadgeCategory.BRONZE,
) -> Badge:
    badge = Badge(name=name, description=f"Descrição de {name}", category=category)
    session.add(badge)
    await session.flush()
    return badge


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token: str = response.json()["data"]["access_token"]
    return token


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class TestBadgeRepository:
    async def test_list_all_returns_created_badges(self, db_session: AsyncSession) -> None:
        await _create_badge(db_session, name="Primeiro Login")
        await _create_badge(db_session, name="Primeira Missão", category=BadgeCategory.PRATA)
        repository = BadgeRepository(db_session)

        badges = await repository.list_all()

        names = {badge.name for badge in badges}
        assert {"Primeiro Login", "Primeira Missão"} <= names

    async def test_get_by_id_returns_none_for_unknown_id(self, db_session: AsyncSession) -> None:
        repository = BadgeRepository(db_session)

        badge = await repository.get_by_id(uuid.uuid4())

        assert badge is None

    async def test_create_persists_a_new_badge(self, db_session: AsyncSession) -> None:
        repository = BadgeRepository(db_session)

        badge = await repository.create(
            name="Debug Hero",
            description="Encontrou e corrigiu um bug em produção",
            category=BadgeCategory.DIAMANTE,
        )

        assert badge.id is not None
        found = await repository.get_by_id(badge.id)
        assert found is not None
        assert found.name == "Debug Hero"


class TestUserBadgeRepository:
    async def test_create_persists_earned_at(self, db_session: AsyncSession) -> None:
        user = await _create_user(
            db_session, email="badge-repo1@claudequest.dev", password="senha-forte"
        )
        badge = await _create_badge(db_session)
        repository = UserBadgeRepository(db_session)

        user_badge = await repository.create(user_id=user.id, badge_id=badge.id)

        assert user_badge.id is not None
        assert user_badge.earned_at is not None

    async def test_get_for_user_and_badge_returns_none_when_not_earned(
        self, db_session: AsyncSession
    ) -> None:
        user = await _create_user(
            db_session, email="badge-repo2@claudequest.dev", password="senha-forte"
        )
        badge = await _create_badge(db_session)
        repository = UserBadgeRepository(db_session)

        result = await repository.get_for_user_and_badge(user_id=user.id, badge_id=badge.id)

        assert result is None


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #


class TestListBadgeCatalog:
    async def test_returns_full_catalog_for_any_authenticated_user(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_badge(db_session, name="Primeiro Login")
        await _create_badge(db_session, name="100 Missões", category=BadgeCategory.OURO)
        await _create_user(
            db_session, email="badge-cat1@claudequest.dev", password="senha-forte"
        )
        token = await _login(
            client_with_db, email="badge-cat1@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/gamification/badges", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        names = {item["name"] for item in data}
        assert {"Primeiro Login", "100 Missões"} <= names

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get("/api/v1/gamification/badges")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


class TestListMyBadges:
    async def test_lists_badges_earned_by_the_logged_in_user(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="badge-me-admin1@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        student = await _create_user(
            db_session, email="badge-me1@claudequest.dev", password="senha-forte"
        )
        badge = await _create_badge(db_session, name="Primeira Missão")
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")
        await client_with_db.post(
            f"/api/v1/gamification/badges/{badge.id}/award",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": str(student.id)},
        )
        student_token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/me/badges",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["badge"]["name"] == "Primeira Missão"
        assert data[0]["badge_id"] == str(badge.id)

    async def test_returns_empty_list_when_user_has_no_badges(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(
            db_session, email="badge-me2@claudequest.dev", password="senha-forte"
        )
        token = await _login(
            client_with_db, email="badge-me2@claudequest.dev", password="senha-forte"
        )

        response = await client_with_db.get(
            "/api/v1/gamification/me/badges", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestAwardBadge:
    async def test_admin_can_award_a_badge_to_a_user(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="badge-award-admin1@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        student = await _create_user(
            db_session, email="badge-award1@claudequest.dev", password="senha-forte"
        )
        badge = await _create_badge(db_session)
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.post(
            f"/api/v1/gamification/badges/{badge.id}/award",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": str(student.id)},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["badge_id"] == str(badge.id)
        assert data["badge"]["name"] == badge.name

    async def test_awarding_the_same_badge_twice_fails_with_a_clear_error(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="badge-award-admin2@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        student = await _create_user(
            db_session, email="badge-award2@claudequest.dev", password="senha-forte"
        )
        badge = await _create_badge(db_session)
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"user_id": str(student.id)}

        first_response = await client_with_db.post(
            f"/api/v1/gamification/badges/{badge.id}/award", headers=headers, json=payload
        )
        second_response = await client_with_db.post(
            f"/api/v1/gamification/badges/{badge.id}/award", headers=headers, json=payload
        )

        assert first_response.status_code == 200
        assert second_response.status_code == 409
        assert second_response.json()["error"]["code"] == "badge_already_awarded"

    async def test_returns_404_for_unknown_badge(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="badge-award-admin3@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        student = await _create_user(
            db_session, email="badge-award3@claudequest.dev", password="senha-forte"
        )
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.post(
            f"/api/v1/gamification/badges/{uuid.uuid4()}/award",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": str(student.id)},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "badge_not_found"

    async def test_non_admin_is_forbidden_from_awarding(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="badge-award4@claudequest.dev", password="senha-forte"
        )
        other_student = await _create_user(
            db_session, email="badge-award5@claudequest.dev", password="senha-forte"
        )
        badge = await _create_badge(db_session)
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.post(
            f"/api/v1/gamification/badges/{badge.id}/award",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(other_student.id)},
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        badge = await _create_badge(db_session)

        response = await client_with_db.post(
            f"/api/v1/gamification/badges/{badge.id}/award",
            json={"user_id": str(badge.id)},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
