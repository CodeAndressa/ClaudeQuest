import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
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


async def test_logout_endpoint_revokes_the_session(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="logout-ok@claudequest.dev", password="senha-correta")
    await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "logout-ok@claudequest.dev", "password": "senha-correta"},
    )

    logout_response = await client_with_db.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["data"]["status"] == "ok"

    refresh_response = await client_with_db.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401


async def test_logout_is_idempotent_without_a_session_cookie(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
