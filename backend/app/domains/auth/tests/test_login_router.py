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


async def test_login_endpoint_returns_access_token_on_success(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="login-ok@claudequest.dev", password="senha-correta")

    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "login-ok@claudequest.dev", "password": "senha-correta"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["access_token"]
    assert body["data"]["user"]["email"] == "login-ok@claudequest.dev"


async def test_login_endpoint_never_returns_refresh_token_in_the_body(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="login-secure@claudequest.dev", password="senha-correta")

    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "login-secure@claudequest.dev", "password": "senha-correta"},
    )

    assert "refresh_token" not in response.json()["data"]


async def test_login_endpoint_sets_httponly_refresh_token_cookie(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="login-cookie@claudequest.dev", password="senha-correta")

    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "login-cookie@claudequest.dev", "password": "senha-correta"},
    )

    cookie = next(c for c in response.cookies.jar if c.name == "refresh_token")
    assert cookie.value
    assert cookie.has_nonstandard_attr("HttpOnly")
    assert cookie.path == "/api/v1/auth"


async def test_login_endpoint_returns_401_on_wrong_password(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="login-fail@claudequest.dev", password="senha-correta")

    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "login-fail@claudequest.dev", "password": "senha-errada"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "invalid_credentials"


async def test_login_endpoint_returns_422_on_missing_fields(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post("/api/v1/auth/login", json={"email": "sem-senha@x.com"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_login_endpoint_returns_422_on_invalid_email_format(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post(
        "/api/v1/auth/login", json={"email": "nao-e-email", "password": "qualquer"}
    )

    assert response.status_code == 422
