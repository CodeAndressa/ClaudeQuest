import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.auth.model import Session as AuthSession
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


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_refresh_endpoint_issues_a_new_access_token(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="refresh-ok@claudequest.dev", password="senha-correta")
    login_response = await _login(
        client_with_db, email="refresh-ok@claudequest.dev", password="senha-correta"
    )
    original_access_token = login_response.json()["data"]["access_token"]

    response = await client_with_db.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["access_token"]
    assert body["data"]["access_token"] != original_access_token
    assert body["data"]["user"]["email"] == "refresh-ok@claudequest.dev"


async def test_refresh_endpoint_rotates_the_session(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="rotate@claudequest.dev", password="senha-correta")
    await _login(client_with_db, email="rotate@claudequest.dev", password="senha-correta")

    await client_with_db.post("/api/v1/auth/refresh")

    sessions = (await db_session.execute(select(AuthSession))).scalars().all()
    assert len(sessions) == 2
    assert sum(1 for s in sessions if s.revoked_at is not None) == 1
    assert sum(1 for s in sessions if s.revoked_at is None) == 1


async def test_refresh_endpoint_returns_401_without_a_cookie(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


async def test_refresh_endpoint_rejects_an_already_used_refresh_token(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="reuse@claudequest.dev", password="senha-correta")
    login_response = await _login(
        client_with_db, email="reuse@claudequest.dev", password="senha-correta"
    )
    old_cookie = login_response.cookies.get("refresh_token")
    assert old_cookie is not None

    await client_with_db.post("/api/v1/auth/refresh")

    client_with_db.cookies.set("refresh_token", old_cookie)
    reuse_response = await client_with_db.post("/api/v1/auth/refresh")

    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "invalid_refresh_token"
