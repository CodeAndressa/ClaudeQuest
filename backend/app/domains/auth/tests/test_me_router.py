import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole, UserStatus


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


async def test_me_endpoint_returns_the_current_user(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="me-ok@claudequest.dev", password="senha-correta")
    login_response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "me-ok@claudequest.dev", "password": "senha-correta"},
    )
    access_token = login_response.json()["data"]["access_token"]

    response = await client_with_db.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "me-ok@claudequest.dev"


async def test_me_endpoint_returns_401_without_authorization_header(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_endpoint_returns_401_with_an_invalid_token(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_endpoint_returns_401_when_the_account_was_blocked_after_login(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(
        db_session, email="me-blocked@claudequest.dev", password="senha-correta"
    )
    login_response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "me-blocked@claudequest.dev", "password": "senha-correta"},
    )
    access_token = login_response.json()["data"]["access_token"]
    user.status = UserStatus.BLOCKED
    await db_session.flush()

    response = await client_with_db.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
