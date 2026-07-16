"""Testes HTTP dos endpoints /auth/forgot-password e /auth/reset-password (AUTH-003)."""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.auth.model import Session as AuthSession
from app.domains.auth.password_reset import PasswordResetToken, hash_reset_token
from app.domains.organizations.model import Organization
from app.domains.users.model import User


async def _create_user(session: AsyncSession, *, email: str, password: str) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.flush()
    return user


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_forgot_password_always_returns_200_for_known_email(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="fp-conhecido@claudequest.dev", password="senha-antiga")

    response = await client_with_db.post(
        "/api/v1/auth/forgot-password", json={"email": "fp-conhecido@claudequest.dev"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


async def test_forgot_password_always_returns_200_for_unknown_email(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post(
        "/api/v1/auth/forgot-password", json={"email": "desconhecido@claudequest.dev"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


async def test_forgot_password_rejects_malformed_email(client_with_db: httpx.AsyncClient) -> None:
    response = await client_with_db.post(
        "/api/v1/auth/forgot-password", json={"email": "nao-e-um-email"}
    )

    assert response.status_code == 422


async def test_reset_password_endpoint_rejects_unknown_token(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post(
        "/api/v1/auth/reset-password",
        json={"token": "token-invalido", "new_password": "senha-nova-123"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


async def test_reset_password_endpoint_rejects_short_password(
    client_with_db: httpx.AsyncClient,
) -> None:
    response = await client_with_db.post(
        "/api/v1/auth/reset-password", json={"token": "qualquer", "new_password": "curta"}
    )

    assert response.status_code == 422


async def test_full_forgot_and_reset_flow_allows_login_with_new_password_and_revokes_old_sessions(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session, email="fluxo-completo@claudequest.dev", password="senha-antiga")

    # 1. Login antes do reset, para provar que a sessão antiga será revogada.
    old_login = await _login(
        client_with_db, email="fluxo-completo@claudequest.dev", password="senha-antiga"
    )
    assert old_login.status_code == 200
    old_refresh_cookie = old_login.cookies.get("refresh_token")
    assert old_refresh_cookie is not None

    # 2. Forgot password - gera o token (logado via structlog, não retornado na API).
    forgot_response = await client_with_db.post(
        "/api/v1/auth/forgot-password", json={"email": "fluxo-completo@claudequest.dev"}
    )
    assert forgot_response.status_code == 200

    reset_token_row = (await db_session.execute(select(PasswordResetToken))).scalars().first()
    assert reset_token_row is not None

    # O teste não tem acesso ao token em texto puro (só o hash foi persistido),
    # então reconstruímos o cenário diretamente para o reset, simulando o link
    # que o usuário clicaria a partir do e-mail.
    from app.domains.auth.password_reset import generate_reset_token

    plain_token, plain_hash = generate_reset_token()
    reset_token_row.token_hash = plain_hash
    await db_session.flush()
    assert hash_reset_token(plain_token) == plain_hash

    # 3. Reset password com o token válido.
    reset_response = await client_with_db.post(
        "/api/v1/auth/reset-password",
        json={"token": plain_token, "new_password": "senha-nova-123"},
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["data"]["status"] == "ok"

    # 4. Login com a senha antiga falha; com a nova, funciona.
    old_password_login = await _login(
        client_with_db, email="fluxo-completo@claudequest.dev", password="senha-antiga"
    )
    assert old_password_login.status_code == 401

    new_password_login = await _login(
        client_with_db, email="fluxo-completo@claudequest.dev", password="senha-nova-123"
    )
    assert new_password_login.status_code == 200

    # 5. A sessão emitida antes do reset foi revogada.
    client_with_db.cookies.set("refresh_token", old_refresh_cookie)
    refresh_with_old_session = await client_with_db.post("/api/v1/auth/refresh")
    assert refresh_with_old_session.status_code == 401

    sessions = (
        (
            await db_session.execute(
                select(AuthSession).where(AuthSession.user_id == reset_token_row.user_id)
            )
        )
        .scalars()
        .all()
    )
    pre_reset_sessions = [s for s in sessions if s.refresh_token_hash != None]  # noqa: E711
    assert any(s.revoked_at is not None for s in pre_reset_sessions)


async def test_reset_password_endpoint_rejects_reused_token(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.domains.auth.password_reset import PasswordResetRepository, generate_reset_token

    user = await _create_user(
        db_session, email="reuse-http@claudequest.dev", password="senha-antiga"
    )
    token, token_hash = generate_reset_token()
    await PasswordResetRepository(db_session).create(
        user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(minutes=30)
    )

    first = await client_with_db.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "senha-nova-123"}
    )
    assert first.status_code == 200

    second = await client_with_db.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "outra-senha-456"}
    )
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "invalid_reset_token"
